"""Variants forked under a base résumé."""

from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import PurePosixPath

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from elena.access import owned_base, owned_variant
from elena.api.deps import BlobStoreDep, SessionDep, SettingsDep, UserIdDep
from elena.api.dto import (
    VariantForkBody,
    VariantForkResponse,
    VariantRead,
    VariantResumeExportResponse,
)
from elena.db.models import StoredResumeDocument
from elena.db.models import Variant as VariantRow
from elena.schemas.resume_document import ResumeDocumentPayload
from elena.storage.blob import BlobRef
from elena.storage.signed_urls import public_signed_download_url

router = APIRouter(tags=["variants"])


def _jd_namespace(user_id: uuid.UUID) -> str:
    return f"jd/{user_id}"


def _stored_jd_path(namespace: str, key: str) -> str:
    return str(PurePosixPath(namespace) / PurePosixPath(key))


@router.post(
    "/bases/{base_id}/variants",
    response_model=VariantForkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def fork_variant(
    base_id: uuid.UUID,
    body: VariantForkBody,
    session: SessionDep,
    user_id: UserIdDep,
    blobs: BlobStoreDep,
    settings: SettingsDep,
) -> VariantForkResponse:
    base = await owned_base(session, user_id, base_id)
    if base.active_document_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="base has no document to fork yet")

    src = await session.get(StoredResumeDocument, base.active_document_id)
    if src is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="broken active_document_id")

    jd_blob_key = None
    jd_text = (body.jd_plaintext or "").strip()
    if jd_text:
        if len(jd_text) > settings.jd_max_plaintext_chars:
            raise HTTPException(
                status.HTTP_413_CONTENT_TOO_LARGE,
                detail=(f"jd_plaintext exceeds jd_max_plaintext_chars ({settings.jd_max_plaintext_chars})"),
            )
        ns = _jd_namespace(user_id)
        bk = f"{uuid.uuid4().hex}.txt"
        blobs.put_bytes(BlobRef(namespace=ns, key=bk), jd_text.encode("utf-8"))
        jd_blob_key = _stored_jd_path(ns, bk)

    label = (body.label or "").strip() or f"job-version-{uuid.uuid4().hex[:8]}"
    new_doc = StoredResumeDocument(
        id=uuid.uuid4(),
        schema_version=src.schema_version,
        payload=deepcopy(src.payload),
        forked_from_id=src.id,
    )
    session.add(new_doc)
    await session.flush()

    now = datetime.now(UTC)
    vr = VariantRow(
        id=uuid.uuid4(),
        base_resume_id=base.id,
        label=label,
        jd_blob_key=jd_blob_key,
        forked_from_document_id=src.id,
        active_document_id=new_doc.id,
        updated_at=now,
    )
    session.add(vr)
    await session.commit()
    await session.refresh(vr)

    jd_download_url = None
    if jd_blob_key is not None:
        p = PurePosixPath(jd_blob_key)
        jd_download_url = public_signed_download_url(
            blobs=blobs,
            settings=settings,
            namespace=str(p.parent),
            key=p.name,
        )

    return VariantForkResponse(variant=VariantRead.model_validate(vr), jd_download_url=jd_download_url)


@router.get("/bases/{base_id}/variants", response_model=list[VariantRead])
async def list_variants(session: SessionDep, user_id: UserIdDep, base_id: uuid.UUID) -> list[VariantRow]:
    await owned_base(session, user_id, base_id)
    res = await session.execute(select(VariantRow).where(VariantRow.base_resume_id == base_id))
    return list(res.scalars().all())


@router.get("/variants/{variant_id}", response_model=VariantRead)
async def get_variant(session: SessionDep, user_id: UserIdDep, variant_id: uuid.UUID) -> VariantRow:
    return await owned_variant(session, user_id, variant_id)


@router.get("/variants/{variant_id}/export", response_model=VariantResumeExportResponse)
async def export_variant_resume_bundle(
    variant_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> VariantResumeExportResponse:
    """Export canonical JSON envelope plus variant metadata (Phase 9.3)."""

    vr = await owned_variant(session, user_id, variant_id)
    if vr.active_document_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="variant has no active document to export")

    dq = await session.execute(
        select(StoredResumeDocument).where(StoredResumeDocument.id == vr.active_document_id),
    )
    stored = dq.scalar_one_or_none()
    if stored is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="broken active_document_id")

    try:
        envelope = ResumeDocumentPayload.model_validate(
            {"schema_version": stored.schema_version, "document": stored.payload},
        )
    except Exception as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"stored payload invalid: {exc!s}",
        ) from exc
    return VariantResumeExportResponse(
        exported_at=datetime.now(UTC),
        variant=VariantRead.model_validate(vr),
        envelope=envelope,
    )


@router.put("/variants/{variant_id}/document", response_model=VariantRead)
async def put_variant_document(
    variant_id: uuid.UUID,
    payload: ResumeDocumentPayload,
    session: SessionDep,
    user_id: UserIdDep,
) -> VariantRow:
    """Persist a new ``StoredResumeDocument`` and set it active on this variant."""

    vr = await owned_variant(session, user_id, variant_id)
    doc_dict = payload.document.model_dump(mode="json")
    rd = StoredResumeDocument(
        id=uuid.uuid4(),
        schema_version=payload.schema_version,
        payload=doc_dict,
        forked_from_id=None,
    )
    session.add(rd)
    await session.flush()
    vr.active_document_id = rd.id
    vr.updated_at = datetime.now(UTC)
    session.add(vr)
    await session.commit()
    await session.refresh(vr)
    return vr


@router.delete("/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variant(session: SessionDep, user_id: UserIdDep, variant_id: uuid.UUID) -> None:
    vr = await owned_variant(session, user_id, variant_id)
    await session.delete(vr)
    await session.commit()
