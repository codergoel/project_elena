"""Shared conversation thread provisioning for bases and variants."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from elena.db.models import ConversationThread


async def ensure_thread_for_base(session: AsyncSession, *, base_resume_id: uuid.UUID) -> ConversationThread:
    """Return existing first thread row for this base, or insert one."""

    existing = await session.execute(
        select(ConversationThread)
        .where(ConversationThread.base_resume_id == base_resume_id)
        .order_by(ConversationThread.created_at.asc())
        .limit(1),
    )
    hit = existing.scalar_one_or_none()
    if hit is not None:
        return hit

    ct = ConversationThread(
        id=uuid.uuid4(),
        langgraph_thread_id=f"stub-web-{uuid.uuid4().hex}",
        base_resume_id=base_resume_id,
        variant_id=None,
    )
    session.add(ct)
    await session.commit()
    await session.refresh(ct)
    return ct


async def ensure_thread_for_variant(session: AsyncSession, *, variant_id: uuid.UUID) -> ConversationThread:
    """Return existing first thread row for this variant, or insert one."""

    existing = await session.execute(
        select(ConversationThread)
        .where(ConversationThread.variant_id == variant_id)
        .order_by(ConversationThread.created_at.asc())
        .limit(1),
    )
    hit = existing.scalar_one_or_none()
    if hit is not None:
        return hit

    ct = ConversationThread(
        id=uuid.uuid4(),
        langgraph_thread_id=f"stub-web-var-{uuid.uuid4().hex}",
        base_resume_id=None,
        variant_id=variant_id,
    )
    session.add(ct)
    await session.commit()
    await session.refresh(ct)
    return ct
