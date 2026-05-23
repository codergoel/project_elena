"""Compile ``StoredResumeDocument`` rows to blob-backed PDF URLs."""

from __future__ import annotations

import time
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from elena.config import Settings
from elena.db.models import StoredResumeDocument
from elena.observability.metrics import observe_latex_compile_duration
from elena.rendering.compiler import compile_resume_tex
from elena.rendering.latex_hints import latex_compile_user_hint
from elena.rendering.tex_builder import resume_document_to_tex
from elena.schemas.resume_document import ResumeDocument
from elena.services.pdf_bundle import PdfRenderBundle
from elena.storage.blob import BlobRef, FilesystemBlobStore


async def pdf_url_from_stored_row(
    session: AsyncSession,
    blobs: FilesystemBlobStore,
    *,
    stored_id: uuid.UUID,
    owning_user_id: uuid.UUID,
    settings: Settings,
) -> PdfRenderBundle:
    """Compile active row JSON → Jake TeX → PDF artifact with signed ``pdf_url``."""

    res = await session.execute(select(StoredResumeDocument).where(StoredResumeDocument.id == stored_id))
    stored = res.scalar_one_or_none()
    if stored is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="document not found")

    try:
        document = ResumeDocument.model_validate(stored.payload)
    except Exception as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"stored payload invalid vs schema: {exc!s}",
        ) from exc

    tex_source = resume_document_to_tex(document)
    latex_t0 = time.perf_counter()
    output = await compile_resume_tex(tex_source, timeout_seconds=float(settings.compile_timeout_seconds))
    observe_latex_compile_duration(output.ok, time.perf_counter() - latex_t0)

    if output.pdf_bytes is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="compile produced no pdf")

    hint = latex_compile_user_hint(output.log_tail)

    key = f"{owning_user_id}/{stored_id}/{uuid.uuid4().hex[:10]}.pdf"
    ref = BlobRef(namespace="artifacts/pdf", key=key)
    blobs.put_bytes(ref, output.pdf_bytes)

    rel = "/api/v1/files/download"
    query = blobs.build_download_query(
        ref,
        ttl_seconds=3600,
        signing_secret=settings.file_download_signing_secret,
    )
    pdf_url = f"{settings.public_api_base_url.rstrip('/')}{rel}{query}"
    return PdfRenderBundle(
        pdf_url=pdf_url,
        compile_ok=output.ok,
        page_count=output.page_count,
        log_tail=output.log_tail,
        latex_user_hint=hint,
    )
