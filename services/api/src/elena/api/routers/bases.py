"""Base résumé CRUD and document payloads."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from elena.access import owned_base
from elena.api.deps import SessionDep, UserIdDep
from elena.api.dto import BaseCreateBody, BaseResumeExportResponse, BaseResumeRead
from elena.db.models import BaseResume as BaseResumeRow
from elena.db.models import StoredResumeDocument
from elena.db.models import Variant as VariantRow
from elena.schemas.resume_document import ResumeDocumentPayload

router = APIRouter(prefix="/bases", tags=["bases"])


@router.post("", response_model=BaseResumeRead)
async def create_base(
    body: BaseCreateBody,
    session: SessionDep,
    user_id: UserIdDep,
) -> BaseResumeRow:
    now = datetime.now(UTC)
    br = BaseResumeRow(
        id=uuid.uuid4(),
        user_id=user_id,
        title=body.title,
        source=body.source,
        active_document_id=None,
        updated_at=now,
    )
    session.add(br)
    await session.commit()
    await session.refresh(br)
    return br


@router.get("", response_model=list[BaseResumeRead])
async def list_bases(session: SessionDep, user_id: UserIdDep) -> list[BaseResumeRow]:
    stmt = select(BaseResumeRow).where(BaseResumeRow.user_id == user_id)
    res = await session.execute(stmt.order_by(BaseResumeRow.created_at.desc()))
    return list(res.scalars().unique().all())


@router.get("/{base_id}", response_model=BaseResumeRead)
async def get_base(session: SessionDep, user_id: UserIdDep, base_id: uuid.UUID) -> BaseResumeRow:
    return await owned_base(session, user_id, base_id)


@router.get("/{base_id}/export", response_model=BaseResumeExportResponse)
async def export_base_resume_bundle(
    base_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> BaseResumeExportResponse:
    """Export canonical JSON envelope plus base metadata for backup (Phase 9.3)."""

    base = await owned_base(session, user_id, base_id)
    if base.active_document_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="base has no active document to export yet")

    dq = await session.execute(
        select(StoredResumeDocument).where(StoredResumeDocument.id == base.active_document_id),
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
    return BaseResumeExportResponse(
        exported_at=datetime.now(UTC),
        resume=BaseResumeRead.model_validate(base),
        envelope=envelope,
    )


@router.delete("/{base_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_base(session: SessionDep, user_id: UserIdDep, base_id: uuid.UUID) -> None:
    row = await owned_base(session, user_id, base_id)
    vc = await session.scalar(
        select(func.count()).select_from(VariantRow).where(VariantRow.base_resume_id == base_id),
    )
    if int(vc or 0) > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "detail": "Delete or move job variants first",
                "variants_remaining": int(vc or 0),
            },
        )
    await session.delete(row)
    await session.commit()


@router.put("/{base_id}/document", response_model=BaseResumeRead)
async def put_base_document(
    base_id: uuid.UUID,
    payload: ResumeDocumentPayload,
    session: SessionDep,
    user_id: UserIdDep,
) -> BaseResumeRow:
    """Persist a validated ``ResumeDocument`` row and flip ``active_document_id``."""

    base = await owned_base(session, user_id, base_id)
    doc_dict = payload.document.model_dump(mode="json")

    rd = StoredResumeDocument(
        id=uuid.uuid4(),
        schema_version=payload.schema_version,
        payload=doc_dict,
        forked_from_id=None,
    )
    session.add(rd)
    await session.flush()
    base.active_document_id = rd.id
    base.updated_at = datetime.now(UTC)
    session.add(base)
    await session.commit()
    await session.refresh(base)
    return base
