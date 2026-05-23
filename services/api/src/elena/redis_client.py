"""Redis singleton used for coarse quotas."""

from __future__ import annotations

import redis.asyncio as redis_module

_redis: redis_module.Redis | None = None


def configure_redis(url: str | None = None, *, redis_obj: redis_module.Redis | None = None) -> None:
    global _redis  # noqa: PLW0603 singleton for app lifespan
    if redis_obj is not None:
        _redis = redis_obj
        return
    if url is None:
        return
    if _redis is not None:
        return
    _redis = redis_module.from_url(url, decode_responses=False)


async def redis_conn() -> redis_module.Redis | None:
    return _redis


async def dispose_redis() -> None:
    """Close pooled connections."""

    global _redis
    r = _redis
    _redis = None
    if r is None:
        return
    await r.aclose()


__all__ = ["configure_redis", "dispose_redis", "redis_conn"]
