"""Shared FastAPI dependencies."""

from __future__ import annotations

import asyncio
import uuid
from typing import Annotated, Any

import jwt
from fastapi import Depends, Header, HTTPException, Request
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from elena.config import Settings, get_settings
from elena.db.models import User
from elena.db.session import get_session
from elena.redis_client import redis_conn
from elena.storage.blob import FilesystemBlobStore

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
RedisDep = Annotated[Any, Depends(redis_conn)]

_blob_store_singleton: FilesystemBlobStore | None = None


def get_blob_store(settings: SettingsDep) -> FilesystemBlobStore:
    global _blob_store_singleton
    if _blob_store_singleton is None:
        settings.blob_storage_root.mkdir(parents=True, exist_ok=True)
        _blob_store_singleton = FilesystemBlobStore(settings.blob_storage_root)
    return _blob_store_singleton


BlobStoreDep = Annotated[FilesystemBlobStore, Depends(get_blob_store)]


async def upsert_oauth_user(
    session: AsyncSession,
    *,
    external_sub: str,
    email: str | None,
) -> User:
    res = await session.execute(select(User).where(User.external_sub == external_sub).limit(1))
    existing = res.scalar_one_or_none()
    if existing is not None:
        return existing
    u = User(id=uuid.uuid4(), external_sub=external_sub, email=email)
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


async def ensure_development_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    res = await session.execute(select(User).where(User.id == user_id).limit(1))
    existing = res.scalar_one_or_none()
    if existing is not None:
        return existing
    u = User(id=user_id, external_sub=None, email=None)
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


async def decode_jwt_sub(token: str, settings: Settings) -> str:
    """Return ``sub`` from validated JWT."""

    def _blocking() -> str:
        if not settings.jwks_url:
            msg = "JWKS_URL is not configured"
            raise RuntimeError(msg)
        header = jwt.get_unverified_header(token)
        alg = header.get("alg") or "RS256"
        jwk_client = PyJWKClient(settings.jwks_url, cache_keys=True)
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        if settings.jwt_audience:
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                audience=settings.jwt_audience,
            )
        else:
            payload = jwt.decode(token, signing_key.key, algorithms=[alg])
        sub = payload.get("sub")
        if not isinstance(sub, str) or not sub:
            raise InvalidTokenError("missing sub claim")
        return sub

    return await asyncio.to_thread(_blocking)


async def authenticated_user_uuid(
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
    x_user_id: Annotated[str | None, Header(alias="x-user-id")] = None,
) -> uuid.UUID:
    """Resolve ``users.id`` from Bearer JWT or (development) ``X-User-Id``."""

    bearer: str | None = None
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        bearer = auth_header.partition(" ")[2].strip() or None

    if settings.auth_mode == "jwks":
        if not bearer:
            raise HTTPException(status_code=401, detail="missing bearer token")
        try:
            sub = await decode_jwt_sub(bearer, settings)
        except (PyJWTError, RuntimeError) as exc:
            raise HTTPException(status_code=401, detail=f"invalid token: {exc!s}") from exc
        u = await upsert_oauth_user(session, external_sub=sub, email=None)
        return u.id

    if x_user_id is None:
        raise HTTPException(
            status_code=401,
            detail='development auth_mode requires header "x-user-id" (uuid)',
        )
    try:
        parsed = uuid.UUID(x_user_id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail="x-user-id must be a valid UUID") from ve
    u = await ensure_development_user(session, parsed)
    return u.id


UserIdDep = Annotated[uuid.UUID, Depends(authenticated_user_uuid)]
