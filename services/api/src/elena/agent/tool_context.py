"""Per-request context for LangGraph tools (DB session + ownership)."""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from elena.config import Settings
from elena.storage.blob import FilesystemBlobStore

AgentMode = Literal["base", "variant"]


@dataclass(frozen=True, slots=True)
class AgentToolContext:
    session: AsyncSession
    user_id: uuid.UUID
    mode: AgentMode
    """Whether we are editing a base résumé or a variant."""
    record_id: uuid.UUID
    """``base_resume_id`` or ``variant_id`` matching ``mode``."""
    blobs: FilesystemBlobStore
    settings: Settings
    redis: Any | None


CURRENT_AGENT_CTX: ContextVar[AgentToolContext | None] = ContextVar("elena_agent_ctx", default=None)
