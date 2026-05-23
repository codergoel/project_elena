"""PDF import pipeline: upload blob, heuristic/LLM preview, commit as base."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import PurePosixPath

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from elena.api.deps import BlobStoreDep, RedisDep, SessionDep, SettingsDep, UserIdDep
from elena.api.dto import (
    BaseResumeRead,
    ImportCommitBody,
    ImportCommitResponse,
    ImportMapBody,
    ImportPdfUploadResponse,
    ImportPreviewResponse,
)
from elena.api.quota import enforce_minute_budget
from elena.config import Settings
from elena.db.models import BaseResume as BaseResumeRow
from elena.db.models import BaseResumeSource, StoredResumeDocument
from elena.import_path.extract_pdf import EncryptedPdfError, extract_text_pdf_bytes, sniff_is_pdf
from elena.import_path.heuristic_mapper import heuristic_map_plaintext
from elena.import_path.llm_mapper import llm_map_plaintext
from elena.storage.blob import BlobRef

router = APIRouter(prefix="/import", tags=["import"])

_PDF_KEY_RE = re.compile(r"^[0-9a-f]{32}\.pdf$")


def _imports_namespace(user_id: uuid.UUID) -> str:
    return f"imports/{user_id}"


def _truncate_text(raw: str, *, limit: int) -> tuple[str, bool]:
    """Return trimmed text plus whether truncation happened."""

    if len(raw) <= limit:
        return raw, False
    return raw[:limit], True


def _require_map_body_exclusive(body: ImportMapBody) -> None:
    has_text = body.extracted_text is not None and body.extracted_text.strip() != ""
    has_key = body.pdf_key is not None and body.pdf_key.strip() != ""
    if has_text == has_key:
        detail = (
            "Provide exactly one of extracted_text or pdf_key"
            if not has_text
            else "Provide only one of extracted_text or pdf_key"
        )
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


async def _text_for_preview(
    body: ImportMapBody,
    *,
    user_id: uuid.UUID,
    blobs: BlobStoreDep,
    settings: Settings,
) -> str:
    _require_map_body_exclusive(body)

    if body.extracted_text is not None:
        txt, truncated = _truncate_text(body.extracted_text.strip(), limit=settings.import_max_extracted_chars)
        if truncated:
            raise HTTPException(
                status.HTTP_413_CONTENT_TOO_LARGE,
                detail=(f"extracted_text exceeds import_max_extracted_chars ({settings.import_max_extracted_chars})"),
            )
        return txt

    pk = body.pdf_key
    assert pk is not None and _PDF_KEY_RE.match(pk)
    ref = BlobRef(namespace=_imports_namespace(user_id), key=pk)
    data = blobs.get_bytes(ref)
    if data is None or not sniff_is_pdf(data[:32]):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="import PDF blob not found")
    try:
        extracted, _pages = extract_text_pdf_bytes(data)
    except EncryptedPdfError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"failed to extract text from PDF: {exc!s}",
        ) from exc
    trimmed, truncated = _truncate_text(extracted, limit=settings.import_max_extracted_chars)
    if truncated:
        extracted = trimmed
    return extracted


def _signed_pdf_url(*, blobs: BlobStoreDep, settings: Settings, ns: str, key: str) -> str:
    q = blobs.build_download_query(
        BlobRef(namespace=ns, key=key),
        ttl_seconds=3600,
        signing_secret=settings.file_download_signing_secret,
    )
    root = settings.public_api_base_url.rstrip("/")
    return f"{root}/api/v1/files/download{q}"


def _stored_pdf_path(namespace: str, key: str) -> str:
    return str(PurePosixPath(namespace) / PurePosixPath(key))


@router.post("/pdf", response_model=ImportPdfUploadResponse)
async def upload_import_pdf(
    session: SessionDep,
    blobs: BlobStoreDep,
    redis_conn: RedisDep,
    settings: SettingsDep,
    user_id: UserIdDep,
    file: UploadFile = File(description="Résumé PDF"),
) -> ImportPdfUploadResponse:
    """Store PDF under ``imports/{user}/…`` (private path) and return extracted text."""

    del session

    await enforce_minute_budget(
        redis_conn,
        scope="import_upload",
        limit=settings.import_upload_quota_per_minute_per_user,
        user_id_key=str(user_id),
    )

    blob = await file.read()
    max_b = settings.import_max_pdf_bytes
    if len(blob) > max_b:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"PDF exceeds limit of {max_b} bytes",
        )
    head = blob[:32]
    if len(blob) < 5 or not sniff_is_pdf(head if len(head) >= 5 else head.ljust(5, b"\0")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="not a PDF file")

    try:
        extracted, page_count = extract_text_pdf_bytes(blob)
    except EncryptedPdfError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"failed to extract text from PDF: {exc!s}",
        ) from exc

    trimmed, truncated = _truncate_text(extracted, limit=settings.import_max_extracted_chars)

    pdf_key = f"{uuid.uuid4().hex}.pdf"
    ns = _imports_namespace(user_id)
    blobs.put_bytes(BlobRef(namespace=ns, key=pdf_key), blob)

    return ImportPdfUploadResponse(
        pdf_key=pdf_key,
        page_count=int(page_count),
        truncated=truncated,
        extracted_chars=len(trimmed),
        extracted_text=trimmed,
    )


@router.post("/preview/heuristic", response_model=ImportPreviewResponse)
async def preview_heuristic(
    body: ImportMapBody,
    session: SessionDep,
    blobs: BlobStoreDep,
    settings: SettingsDep,
    user_id: UserIdDep,
) -> ImportPreviewResponse:
    del session

    text = await _text_for_preview(body, user_id=user_id, blobs=blobs, settings=settings)
    result = heuristic_map_plaintext(text)
    return ImportPreviewResponse(
        resume=result.envelope,
        user_profile=result.user_profile,
        field_confidence=result.field_confidence,
        overall_confidence=result.overall_confidence,
    )


@router.post("/preview/llm", response_model=ImportPreviewResponse)
async def preview_llm(
    body: ImportMapBody,
    session: SessionDep,
    blobs: BlobStoreDep,
    redis_conn: RedisDep,
    settings: SettingsDep,
    user_id: UserIdDep,
) -> ImportPreviewResponse:
    del session

    await enforce_minute_budget(
        redis_conn,
        scope="import_llm",
        limit=settings.import_llm_quota_per_minute_per_user,
        user_id_key=str(user_id),
    )

    text = await _text_for_preview(body, user_id=user_id, blobs=blobs, settings=settings)
    result = await llm_map_plaintext(text, settings)
    return ImportPreviewResponse(
        resume=result.envelope,
        user_profile=result.user_profile,
        field_confidence=result.field_confidence,
        overall_confidence=result.overall_confidence,
    )


@router.post("/commit", response_model=ImportCommitResponse)
async def commit_import(
    body: ImportCommitBody,
    session: SessionDep,
    blobs: BlobStoreDep,
    settings: SettingsDep,
    user_id: UserIdDep,
) -> ImportCommitResponse:
    """Create a ``BaseResume`` row with ``source=import``, optional stored PDF pointer."""

    ns = _imports_namespace(user_id)
    stored_path: str | None = None
    pdf_url: str | None = None

    if body.pdf_key is not None:
        pk = body.pdf_key
        if not _PDF_KEY_RE.match(pk):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="invalid pdf_key")
        ref = BlobRef(namespace=ns, key=pk)
        if blobs.get_bytes(ref) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="import PDF blob not found")
        stored_path = _stored_pdf_path(ns, pk)
        pdf_url = _signed_pdf_url(blobs=blobs, settings=settings, ns=ns, key=pk)

    now = datetime.now(UTC)
    br = BaseResumeRow(
        id=uuid.uuid4(),
        user_id=user_id,
        title=body.title,
        source=BaseResumeSource.IMPORT,
        active_document_id=None,
        updated_at=now,
        import_source_pdf_key=stored_path,
        import_user_profile=body.user_profile.model_dump(mode="json"),
    )
    session.add(br)
    doc_dict = body.envelope.document.model_dump(mode="json")

    rd = StoredResumeDocument(
        id=uuid.uuid4(),
        schema_version=str(body.envelope.schema_version),
        payload=doc_dict,
        forked_from_id=None,
    )
    session.add(rd)
    await session.flush()

    br.active_document_id = rd.id
    br.updated_at = now
    session.add(br)

    await session.commit()
    await session.refresh(br)
    return ImportCommitResponse(
        base_resume=BaseResumeRead.model_validate(br),
        source_pdf_download_url=pdf_url,
    )
