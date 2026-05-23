"""Coarse Redis-backed compile quota."""

from __future__ import annotations

import time
from typing import Any

from fastapi import HTTPException

from elena.observability.metrics import observe_quota_rejection


async def enforce_compile_budget(redis_conn: Any, *, limit: int, user_id_key: str) -> None:
    """Fixed window quota per Unix minute."""

    if redis_conn is None:
        return

    bucket = int(time.time() // 60)
    redis_key = f"quota:compile:{user_id_key}:{bucket}"

    incr = await redis_conn.incr(redis_key)
    if incr == 1:
        await redis_conn.expire(redis_key, 120)

    if incr > limit:
        observe_quota_rejection("compile")
        remaining = bucket * 60 + 60 - int(time.time())
        raise HTTPException(
            status_code=429,
            detail=f"compile rate limited; resets in approx {remaining}s",
        )


async def enforce_minute_budget(
    redis_conn: Any,
    *,
    scope: str,
    limit: int,
    user_id_key: str,
) -> None:
    """Fixed-window per-minute quota (same bucket semantics as compile)."""

    if redis_conn is None:
        return

    bucket = int(time.time() // 60)
    redis_key = f"quota:{scope}:{user_id_key}:{bucket}"

    incr = await redis_conn.incr(redis_key)
    if incr == 1:
        await redis_conn.expire(redis_key, 120)

    if incr > limit:
        observe_quota_rejection(scope)
        remaining = bucket * 60 + 60 - int(time.time())
        raise HTTPException(
            status_code=429,
            detail=f"{scope} rate limited; resets in approx {remaining}s",
        )
