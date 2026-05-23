"""HTTP access log + Prometheus buckets (Phase 10.2)."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from elena.observability.metrics import matched_route_template, observe_http

ACCESS_LOG = logging.getLogger("elena.access")


class AccessMetricsMiddleware(BaseHTTPMiddleware):
    """Record HTTP latency distributions and structured access lines."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        resp: Response = await call_next(request)
        duration = time.perf_counter() - start
        tpl = matched_route_template(request.scope)
        method = request.method
        status = resp.status_code
        observe_http(method, tpl, status, duration)

        rid = getattr(request.state, "request_id", None)
        duration_ms = duration * 1000.0
        ACCESS_LOG.info(
            "%s %s -> %s in %.3f ms request_id=%s",
            method,
            tpl,
            status,
            duration_ms,
            rid or "",
        )
        return resp
