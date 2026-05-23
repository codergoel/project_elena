"""Metrics and middleware wiring (Phase 10)."""

import pytest
from httpx import ASGITransport, AsyncClient

from elena.api.main import app
from elena.config import get_settings


@pytest.mark.asyncio
async def test_metrics_disabled_returns_404() -> None:
    get_settings.cache_clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_metrics_when_enabled_contains_series(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPOSE_PROMETHEUS_METRICS", "true")
    get_settings.cache_clear()
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            hb = await client.get("/health")
            assert hb.status_code == 200
            metrics = await client.get("/metrics")
    finally:
        monkeypatch.delenv("EXPOSE_PROMETHEUS_METRICS", raising=False)
        get_settings.cache_clear()

    assert metrics.status_code == 200
    body = metrics.text
    assert "http_requests_total" in body


@pytest.mark.asyncio
async def test_health_request_has_request_header() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert "x-request-id" in resp.headers
