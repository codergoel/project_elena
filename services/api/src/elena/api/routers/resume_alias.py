"""Checkpoint naming alias — ``resume_id`` is a base résumé id."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from elena.access import owned_base
from elena.api.deps import BlobStoreDep, RedisDep, SessionDep, SettingsDep, UserIdDep
from elena.api.dto import RenderResponse
from elena.api.routers.pdf_routes import _render_for_active_document

router = APIRouter(tags=["checkpoint-alias"])


@router.post("/resumes/{resume_id}/render", response_model=RenderResponse)
async def resume_alias_render(
    resume_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
    blobs: BlobStoreDep,
    settings: SettingsDep,
    redis: RedisDep,
) -> RenderResponse:
    """Same semantics as ``POST /bases/{id}/render`` (``resume_id`` = base id)."""

    base = await owned_base(session, user_id, resume_id)
    return await _render_for_active_document(
        stored_id=base.active_document_id,
        session=session,
        user_id=user_id,
        blobs=blobs,
        settings=settings,
        redis=redis,
    )
