"""Attach ``X-Request-ID`` per request for support correlation (Phase 10-lite)."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from elena.observability.request_context import current_request_id


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        rid_header = request.headers.get("x-request-id")
        if rid_header is not None and rid_header.strip():
            rid = rid_header.strip()[:128]
        else:
            rid = str(uuid.uuid4())
        request.state.request_id = rid
        token = current_request_id.set(rid)
        try:
            resp: Response = await call_next(request)
            resp.headers["X-Request-ID"] = rid
            return resp
        finally:
            current_request_id.reset(token)
