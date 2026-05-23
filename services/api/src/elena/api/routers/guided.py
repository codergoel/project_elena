"""Phase 6 — guided skeleton intake (deterministic slot FSM)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import cast

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from elena.access import owned_base
from elena.api.deps import SessionDep, UserIdDep
from elena.api.dto import (
    BaseResumeRead,
    GuidedBootstrapResponse,
    GuidedCheckpointRead,
    GuidedEducationCommitBody,
    GuidedExperienceCommitBody,
    GuidedHeadingCommitBody,
    GuidedSkillsCommitBody,
    GuidedStatusResponse,
)
from elena.db.models import BaseResume as BaseResumeRow
from elena.db.models import BaseResumeSource, StoredResumeDocument
from elena.guided_fsm import (
    SLOT_PROMPTS,
    apply_education,
    apply_experience,
    apply_heading_patch,
    apply_skills,
    bootstrap_envelope,
    next_pending_slot,
    parse_checkpoint,
)
from elena.schemas.resume_document import ResumeDocument, ResumeDocumentPayload
from elena.schemas.versioning import ResumeSchemaVersionV1

router = APIRouter(tags=["guided"])


async def _load_envelope(session: SessionDep, base: BaseResumeRow) -> ResumeDocumentPayload | None:
    aid = base.active_document_id
    if aid is None:
        return None
    res = await session.execute(select(StoredResumeDocument).where(StoredResumeDocument.id == aid))
    row = res.scalar_one_or_none()
    if row is None:
        return None
    return ResumeDocumentPayload(
        schema_version=cast(ResumeSchemaVersionV1, row.schema_version),
        document=ResumeDocument.model_validate(row.payload),
    )


async def _persist_guided_document(
    session: SessionDep,
    base: BaseResumeRow,
    envelope: ResumeDocumentPayload,
    checkpoint: GuidedCheckpointRead | None = None,
) -> BaseResumeRow:
    rd = StoredResumeDocument(
        id=uuid.uuid4(),
        schema_version=envelope.schema_version,
        payload=envelope.document.model_dump(mode="json"),
        forked_from_id=None,
    )
    session.add(rd)
    await session.flush()
    base.active_document_id = rd.id
    base.updated_at = datetime.now(UTC)
    if checkpoint is not None:
        base.guided_checkpoint = {"skipped": list(checkpoint.skipped_slots)}
    session.add(base)
    await session.commit()
    await session.refresh(base)
    return base


def _guided_checkpoint(row: BaseResumeRow) -> GuidedCheckpointRead:
    cp = parse_checkpoint(row.guided_checkpoint)
    return GuidedCheckpointRead(skipped_slots=list(cp.skipped))


def _status(base: BaseResumeRow, envelope: ResumeDocumentPayload | None) -> GuidedStatusResponse:
    if envelope is None:
        return GuidedStatusResponse(
            bootstrap_required=True,
            terminal=False,
            next_slot=None,
            prompt=None,
            checkpoint=_guided_checkpoint(base),
            resume=None,
        )
    cp = parse_checkpoint(base.guided_checkpoint)
    nxt = next_pending_slot(envelope.document, cp)
    term = nxt is None
    prompt = SLOT_PROMPTS[nxt] if nxt is not None else None
    return GuidedStatusResponse(
        bootstrap_required=False,
        terminal=term,
        next_slot=nxt,
        prompt=prompt,
        checkpoint=_guided_checkpoint(base),
        resume=envelope,
    )


def _require_guided_base(base: BaseResumeRow) -> None:
    if base.source != BaseResumeSource.GUIDED:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="guided endpoints are limited to bases with source=guided",
        )


@router.get("/bases/{base_id}/guided/status", response_model=GuidedStatusResponse)
async def guided_status(
    base_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> GuidedStatusResponse:
    base = await owned_base(session, user_id, base_id)
    _require_guided_base(base)
    env = await _load_envelope(session, base)
    return _status(base, env)


@router.post("/bases/{base_id}/guided/bootstrap", response_model=GuidedBootstrapResponse)
async def guided_bootstrap(
    base_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> GuidedBootstrapResponse:
    base = await owned_base(session, user_id, base_id)
    _require_guided_base(base)
    if base.active_document_id is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="base already has a document — bootstrap skipped",
        )
    env = bootstrap_envelope()
    await _persist_guided_document(session, base, env, checkpoint=GuidedCheckpointRead(skipped_slots=[]))
    await session.refresh(base)
    return GuidedBootstrapResponse(base_resume=BaseResumeRead.model_validate(base))


@router.post("/bases/{base_id}/guided/step/heading", response_model=BaseResumeRead)
async def guided_heading(
    base_id: uuid.UUID,
    body: GuidedHeadingCommitBody,
    session: SessionDep,
    user_id: UserIdDep,
) -> BaseResumeRow:
    base = await owned_base(session, user_id, base_id)
    _require_guided_base(base)
    env = await _load_envelope(session, base)
    if env is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="call /guided/bootstrap first")
    cp_model = parse_checkpoint(base.guided_checkpoint)
    pend = next_pending_slot(env.document, cp_model)
    if pend != "heading":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f'expected guided slot "heading"; current pending slot is "{pend}"',
        )
    new_doc = apply_heading_patch(
        env.document,
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        address_line=body.address_line,
        linkedin_url=body.linkedin_url,
        github_url=body.github_url,
    )
    envelope = ResumeDocumentPayload(schema_version=env.schema_version, document=new_doc)
    return await _persist_guided_document(session, base, envelope, checkpoint=_guided_checkpoint(base))


@router.post("/bases/{base_id}/guided/step/education", response_model=BaseResumeRead)
async def guided_education(
    base_id: uuid.UUID,
    body: GuidedEducationCommitBody,
    session: SessionDep,
    user_id: UserIdDep,
) -> BaseResumeRow:
    base = await owned_base(session, user_id, base_id)
    _require_guided_base(base)
    env = await _load_envelope(session, base)
    if env is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="call /guided/bootstrap first")
    cp_model = parse_checkpoint(base.guided_checkpoint)
    pend = next_pending_slot(env.document, cp_model)
    if pend != "education":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f'expected guided slot "education"; current pending slot is "{pend}"',
        )
    try:
        new_doc, new_cp = apply_education(env.document, cp=cp_model, skip=body.skip, entry=body.entry)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    envelope = ResumeDocumentPayload(schema_version=env.schema_version, document=new_doc)
    ack = GuidedCheckpointRead(skipped_slots=list(new_cp.skipped))
    return await _persist_guided_document(session, base, envelope, checkpoint=ack)


@router.post("/bases/{base_id}/guided/step/experience", response_model=BaseResumeRead)
async def guided_experience(
    base_id: uuid.UUID,
    body: GuidedExperienceCommitBody,
    session: SessionDep,
    user_id: UserIdDep,
) -> BaseResumeRow:
    base = await owned_base(session, user_id, base_id)
    _require_guided_base(base)
    env = await _load_envelope(session, base)
    if env is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="call /guided/bootstrap first")
    cp_model = parse_checkpoint(base.guided_checkpoint)
    pend = next_pending_slot(env.document, cp_model)
    if pend != "experience":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f'expected guided slot "experience"; current pending slot is "{pend}"',
        )
    try:
        new_doc, new_cp = apply_experience(
            env.document,
            cp=cp_model,
            skip=body.skip,
            entry=body.entry,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    envelope = ResumeDocumentPayload(schema_version=env.schema_version, document=new_doc)
    ack = GuidedCheckpointRead(skipped_slots=list(new_cp.skipped))
    return await _persist_guided_document(session, base, envelope, checkpoint=ack)


@router.post("/bases/{base_id}/guided/step/skills", response_model=BaseResumeRead)
async def guided_skills(
    base_id: uuid.UUID,
    body: GuidedSkillsCommitBody,
    session: SessionDep,
    user_id: UserIdDep,
) -> BaseResumeRow:
    base = await owned_base(session, user_id, base_id)
    _require_guided_base(base)
    env = await _load_envelope(session, base)
    if env is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="call /guided/bootstrap first")
    cp_model = parse_checkpoint(base.guided_checkpoint)
    pend = next_pending_slot(env.document, cp_model)
    if pend != "skills":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f'expected guided slot "skills"; current pending slot is "{pend}"',
        )
    try:
        new_doc, new_cp = apply_skills(
            env.document,
            cp=cp_model,
            skip=body.skip,
            languages=body.languages,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    envelope = ResumeDocumentPayload(schema_version=env.schema_version, document=new_doc)
    ack = GuidedCheckpointRead(skipped_slots=list(new_cp.skipped))
    return await _persist_guided_document(session, base, envelope, checkpoint=ack)
