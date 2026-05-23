"""Prometheus metrics (scraped from ``GET /metrics`` when enabled)."""

from __future__ import annotations

from collections.abc import Mapping

from prometheus_client import Counter, Histogram

_HTTP_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 30.0, 120.0)
_LATEX_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 90, 120)

http_requests_total = Counter(
    "http_requests_total",
    "Inbound HTTP responses by route template, status class, and verb",
    ["method", "route", "status_class"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "End-to-end HTTP latency observed at ASGI middleware (route template cardinality)",
    ["method", "route", "status_class"],
    buckets=_HTTP_BUCKETS,
)

latex_compile_total = Counter(
    "elena_latex_compile_total",
    "LaTeX subprocess outcomes (resume PDF spine)",
    ["ok"],
)

latex_compile_duration_seconds = Histogram(
    "elena_latex_compile_duration_seconds",
    "Wall time of ``compile_resume_tex`` (subprocess) per attempt",
    buckets=_LATEX_BUCKETS,
)

quota_rejection_total = Counter(
    "elena_quota_rejection_total",
    "HTTP 429 responses from Redis fixed-window quotas (label ``scope`` matches bucket key)",
    ["scope"],
)

agent_turn_total = Counter(
    "elena_agent_turn_total",
    "Editor agent synchronous turns (counts each POST …/agent/turn)",
    ["outcome"],
)

agent_turn_wall_seconds = Histogram(
    "elena_agent_turn_wall_seconds",
    "Wall time for LangGraph agent ``ainvoke`` per POST …/agent/turn",
    buckets=_HTTP_BUCKETS,
)

import_llm_calls_total = Counter(
    "elena_import_llm_calls_total",
    "LLM-based PDF-import mapping attempts grouped by coarse outcome",
    ["outcome"],
)


def observe_http(method: str, route_template: str, status_code: int, duration_seconds: float) -> None:
    """Record request latency + counter for alerting on error rates."""

    klass = _status_class(status_code)
    labels = dict(method=method.upper(), route=route_template, status_class=klass)
    http_requests_total.labels(**labels).inc()
    http_request_duration_seconds.labels(**labels).observe(duration_seconds)


def observe_latex_compile_duration(ok: bool, duration_seconds: float) -> None:
    latex_compile_total.labels(ok=str(ok).lower()).inc()
    latex_compile_duration_seconds.observe(duration_seconds)


def observe_quota_rejection(scope: str) -> None:
    quota_rejection_total.labels(scope=scope).inc()


def observe_agent_turn_outcome(outcome: str, duration_seconds: float) -> None:
    """``outcome`` is ``success`` or ``graph_exception``."""

    agent_turn_total.labels(outcome=outcome).inc()
    agent_turn_wall_seconds.observe(duration_seconds)


def observe_import_llm_outcome(outcome: str) -> None:
    """``outcome`` is ``success`` or ``failure``."""

    import_llm_calls_total.labels(outcome=outcome).inc()


def _status_class(code: int) -> str:
    if 200 <= code < 300:
        return "2xx"
    if 300 <= code < 400:
        return "3xx"
    if 400 <= code < 500:
        return "4xx"
    return "5xx"


def matched_route_template(request_scope: Mapping[str, object]) -> str:
    """Return Starlette/FastAPI path template (low label cardinality); raw path if unmatched."""

    route = request_scope.get("route")
    path_tpl = getattr(route, "path", None) if route is not None else None
    if path_tpl:
        root = getattr(route, "root_path", "") or ""
        tpl = str(path_tpl)
        if root:
            sep = "" if tpl.startswith("/") else "/"
            return f"{root.rstrip('/')}{sep}{tpl}"
        return tpl
    raw = request_scope.get("path")
    return str(raw) if raw else "unknown"
