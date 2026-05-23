"""Render active ``ResumeDocument`` rows to Jake-template PDF."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from elena.access import owned_base, owned_variant
from elena.api.deps import BlobStoreDep, RedisDep, SessionDep, SettingsDep, UserIdDep
from elena.api.dto import RenderResponse
from elena.api.quota import enforce_compile_budget
from elena.services.render_pdf import pdf_url_from_stored_row

router = APIRouter(tags=["render"])


async def _render_for_active_document(
    *,
    stored_id: uuid.UUID | None,
    session: SessionDep,
    user_id: uuid.UUID,
    blobs: BlobStoreDep,
    settings: SettingsDep,
    redis: RedisDep,
) -> RenderResponse:
    if stored_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="no active document configured")

    await enforce_compile_budget(
        redis,
        limit=settings.compile_quota_per_minute_per_user,
        user_id_key=str(user_id),
    )

    bundle = await pdf_url_from_stored_row(
        session,
        blobs,
        stored_id=stored_id,
        owning_user_id=user_id,
        settings=settings,
    )
    return RenderResponse(
        pdf_url=bundle.pdf_url,
        compile_ok=bundle.compile_ok,
        page_count=bundle.page_count,
        log_tail=bundle.log_tail,
        latex_user_hint=bundle.latex_user_hint,
    )


@router.post("/bases/{base_id}/render", response_model=RenderResponse)
async def render_base_pdf(
    base_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
    blobs: BlobStoreDep,
    settings: SettingsDep,
    redis: RedisDep,
) -> RenderResponse:
    base = await owned_base(session, user_id, base_id)
    return await _render_for_active_document(
        stored_id=base.active_document_id,
        session=session,
        user_id=user_id,
        blobs=blobs,
        settings=settings,
        redis=redis,
    )


@router.post("/variants/{variant_id}/render", response_model=RenderResponse)
async def render_variant_pdf(
    variant_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
    blobs: BlobStoreDep,
    settings: SettingsDep,
    redis: RedisDep,
) -> RenderResponse:
    variant = await owned_variant(session, user_id, variant_id)
    return await _render_for_active_document(
        stored_id=variant.active_document_id,
        session=session,
        user_id=user_id,
        blobs=blobs,
        settings=settings,
        redis=redis,
    )
