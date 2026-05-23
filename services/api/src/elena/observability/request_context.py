"""Per-request identifiers for logs and downstream correlation (Phase 10)."""

from __future__ import annotations

from contextvars import ContextVar

# Set by RequestIDMiddleware for the lifetime of request handling inside call_next().
current_request_id: ContextVar[str | None] = ContextVar("elena_current_request_id", default=None)
