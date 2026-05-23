"""Authorization helpers."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from elena.db.models import BaseResume as BaseResumeRow
from elena.db.models import Variant as VariantRow


async def owned_base(session: AsyncSession, user_id: uuid.UUID, base_id: uuid.UUID) -> BaseResumeRow:
    res = await session.execute(select(BaseResumeRow).where(BaseResumeRow.id == base_id))
    row = res.scalar_one_or_none()
    if row is None or row.user_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="base not found or access denied")
    return row


async def owned_variant(session: AsyncSession, user_id: uuid.UUID, variant_id: uuid.UUID) -> VariantRow:
    stmt = (
        select(VariantRow)
        .join(BaseResumeRow, VariantRow.base_resume_id == BaseResumeRow.id)
        .where(VariantRow.id == variant_id)
        .where(BaseResumeRow.user_id == user_id)
    )
    res = await session.execute(stmt)
    variant = res.scalar_one_or_none()
    if variant is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="variant not found or access denied")
    return variant
