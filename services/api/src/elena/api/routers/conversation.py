"""Conversation thread provisioning (Phase 7.2).

LangGraph checkpoints use ``conversation_threads.id`` as thread key (Phase 7.3).

One thread row per base or per variant is created on demand via ``POST``;
reuse on subsequent ``POST``.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from elena.access import owned_base, owned_variant
from elena.api.deps import SessionDep, UserIdDep
from elena.api.dto import ConversationThreadRead
from elena.conversation.threads import ensure_thread_for_base, ensure_thread_for_variant
from elena.db.models import ConversationThread

router = APIRouter(tags=["conversation"])


@router.get("/bases/{base_id}/thread", response_model=ConversationThreadRead)
async def get_base_thread(
    base_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> ConversationThread:
    """Return the first conversation thread tied to this base, if any."""

    await owned_base(session, user_id, base_id)
    res = await session.execute(
        select(ConversationThread)
        .where(ConversationThread.base_resume_id == base_id)
        .order_by(ConversationThread.created_at.asc())
        .limit(1),
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no conversation thread for this base")
    return row


@router.post("/bases/{base_id}/thread", response_model=ConversationThreadRead)
async def ensure_base_thread(
    base_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> ConversationThread:
    """Get or create a stub ``langgraph_thread_id`` bound to ``base_resume_id``."""

    await owned_base(session, user_id, base_id)
    return await ensure_thread_for_base(session, base_resume_id=base_id)


@router.get("/variants/{variant_id}/thread", response_model=ConversationThreadRead)
async def get_variant_thread(
    variant_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> ConversationThread:
    """Return the first conversation thread tied to this variant, if any."""

    await owned_variant(session, user_id, variant_id)
    res = await session.execute(
        select(ConversationThread)
        .where(ConversationThread.variant_id == variant_id)
        .order_by(ConversationThread.created_at.asc())
        .limit(1),
    )
    row = res.scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no conversation thread for this variant")
    return row


@router.post("/variants/{variant_id}/thread", response_model=ConversationThreadRead)
async def ensure_variant_thread(
    variant_id: uuid.UUID,
    session: SessionDep,
    user_id: UserIdDep,
) -> ConversationThread:
    """Get or create a stub ``langgraph_thread_id`` bound to ``variant_id``."""

    await owned_variant(session, user_id, variant_id)
    return await ensure_thread_for_variant(session, variant_id=variant_id)
