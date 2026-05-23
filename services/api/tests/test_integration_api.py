"""End-to-end API behaviour (needs Postgres + Redis + migrations)."""

from __future__ import annotations

import io
import json
import uuid
from pathlib import Path
from urllib.parse import urlparse

import pytest
from reportlab.pdfgen import canvas
from starlette.testclient import TestClient

from elena.api.main import create_app
from elena.config import get_settings

FIXTURES = Path(__file__).resolve().parent / "fixtures"

pytestmark = pytest.mark.integration


@pytest.fixture
def client() -> TestClient:
    """Fresh Settings cache each test — env overrides (limits, URLs) remain isolated."""

    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as tc:
        yield tc
    get_settings.cache_clear()


def test_base_document_variant_delete_flow(client: TestClient) -> None:
    uid = str(uuid.uuid4())
    headers = {"x-user-id": uid}

    r = client.post(
        "/api/v1/bases",
        json={"title": "My SWE base", "source": "guided"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    base_id = r.json()["id"]

    doc = json.loads((FIXTURES / "resume_minimal.json").read_text())
    r2 = client.put(
        f"/api/v1/bases/{base_id}/document",
        json={"schema_version": "1", "document": doc},
        headers=headers,
    )
    assert r2.status_code == 200, r2.text

    r3 = client.post(
        f"/api/v1/bases/{base_id}/variants",
        json={"label": "Acme"},
        headers=headers,
    )
    assert r3.status_code == 201, r3.text
    variant_id = r3.json()["variant"]["id"]

    r_del_base = client.delete(f"/api/v1/bases/{base_id}", headers=headers)
    assert r_del_base.status_code == 409, r_del_base.text

    r_del_v = client.delete(f"/api/v1/variants/{variant_id}", headers=headers)
    assert r_del_v.status_code == 204, r_del_v.text

    r_del_base2 = client.delete(f"/api/v1/bases/{base_id}", headers=headers)
    assert r_del_base2.status_code == 204, r_del_base2.text


def _import_fixture_pdf_bytes() -> bytes:
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf)
    y = 800
    for line in ("Taylor ImportBot", "taylor@import.example.net", "- Shipped infra at Acme Labs"):
        pdf.drawString(72, y, line)
        y -= 24
    pdf.showPage()
    pdf.save()
    return buf.getvalue()


def test_import_pdf_upload_preview_commit_roundtrip(client: TestClient) -> None:
    uid = str(uuid.uuid4())
    headers = {"x-user-id": uid}

    pdf_bytes = _import_fixture_pdf_bytes()
    ru = client.post(
        "/api/v1/import/pdf",
        headers=headers,
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert ru.status_code == 200, ru.text
    up = ru.json()
    pk = str(up["pdf_key"])
    assert pk.endswith(".pdf")

    rp = client.post(
        "/api/v1/import/preview/heuristic",
        headers=headers,
        json={"pdf_key": pk},
    )
    assert rp.status_code == 200, rp.text
    prev = rp.json()
    envelope = prev["resume"]
    assert envelope["document"]["heading"]["full_name"] == "Taylor ImportBot"

    rc = client.post(
        "/api/v1/import/commit",
        headers=headers,
        json={
            "title": "Taylor base",
            "envelope": envelope,
            "user_profile": prev.get("user_profile") or {},
            "pdf_key": pk,
        },
    )
    assert rc.status_code == 200, rc.text
    out = rc.json()
    bid = uuid.UUID(out["base_resume"]["id"])
    src = str(out["base_resume"].get("import_source_pdf_key") or "")
    assert "imports/" in src and pk in src
    assert isinstance(out.get("source_pdf_download_url"), str)

    rg = client.get(f"/api/v1/bases/{bid}", headers=headers)
    assert rg.status_code == 200
    rd = rg.json()
    assert rd["title"] == "Taylor base"
    assert rd["source"] == "import"
    assert rd.get("active_document_id")
    assert rd.get("import_source_pdf_key")


def test_guided_flow_bootstrap_through_skipping(client: TestClient) -> None:
    uid = str(uuid.uuid4())
    headers = {"x-user-id": uid}

    rb = client.post(
        "/api/v1/bases",
        json={"title": "Guided test base", "source": "guided"},
        headers=headers,
    )
    assert rb.status_code == 200, rb.text
    bid = uuid.UUID(rb.json()["id"])

    boot = client.post(f"/api/v1/bases/{bid}/guided/bootstrap", headers=headers)
    assert boot.status_code == 200, boot.text

    h = client.post(
        f"/api/v1/bases/{bid}/guided/step/heading",
        headers={**headers, "Content-Type": "application/json"},
        json={"full_name": "Morgan Jules", "email": "morgan+jules@example.com"},
    )
    assert h.status_code == 200, h.text

    for path, payload in (
        ("education", {"skip": True}),
        ("experience", {"skip": True}),
        ("skills", {"skip": True}),
    ):
        rstep = client.post(
            f"/api/v1/bases/{bid}/guided/step/{path}",
            headers={**headers, "Content-Type": "application/json"},
            json=payload,
        )
        assert rstep.status_code == 200, rstep.text

    rs = client.get(f"/api/v1/bases/{bid}/guided/status", headers=headers)
    assert rs.status_code == 200, rs.text
    body = rs.json()
    assert body["terminal"] is True
    assert body["resume"]["document"]["heading"]["full_name"] == "Morgan Jules"


def test_thread_ensure_idempotent_for_base(client: TestClient) -> None:
    uid = str(uuid.uuid4())
    headers = {"x-user-id": uid}

    rb = client.post(
        "/api/v1/bases",
        json={"title": "Thread smoke base", "source": "guided"},
        headers=headers,
    )
    assert rb.status_code == 200, rb.text
    bid = uuid.UUID(rb.json()["id"])

    g404 = client.get(f"/api/v1/bases/{bid}/thread", headers=headers)
    assert g404.status_code == 404, g404.text

    po = client.post(f"/api/v1/bases/{bid}/thread", headers=headers)
    assert po.status_code == 200, po.text
    j = po.json()
    tid_first = str(j["id"])
    lg_first = str(j["langgraph_thread_id"])

    g2 = client.get(f"/api/v1/bases/{bid}/thread", headers=headers)
    assert g2.status_code == 200
    assert str(g2.json()["id"]) == tid_first
    assert str(g2.json()["langgraph_thread_id"]) == lg_first

    po2 = client.post(f"/api/v1/bases/{bid}/thread", headers=headers)
    assert po2.status_code == 200
    assert str(po2.json()["id"]) == tid_first
    assert str(po2.json()["langgraph_thread_id"]) == lg_first


def test_variant_fork_jd_signed_download_put_document(client: TestClient) -> None:
    uid = str(uuid.uuid4())
    headers = {"x-user-id": uid}

    rb = client.post(
        "/api/v1/bases",
        json={"title": "Tailor base", "source": "guided"},
        headers=headers,
    )
    assert rb.status_code == 200, rb.text
    bid = str(rb.json()["id"])

    doc = json.loads((FIXTURES / "resume_minimal.json").read_text())
    rdoc = client.put(
        f"/api/v1/bases/{bid}/document",
        json={"schema_version": "1", "document": doc},
        headers=headers,
    )
    assert rdoc.status_code == 200, rdoc.text

    jd_line = "We need a pragmatic backend engineer familiar with Postgres."
    rf = client.post(
        f"/api/v1/bases/{bid}/variants",
        headers=headers,
        json={"label": "MegaCorp", "jd_plaintext": jd_line},
    )
    assert rf.status_code == 201, rf.text
    out = rf.json()
    vid = str(out["variant"]["id"])
    jd_url = out.get("jd_download_url")
    assert isinstance(jd_url, str) and jd_url.startswith("http")

    parsed = urlparse(jd_url)
    dl = client.get(f"{parsed.path}?{parsed.query}")
    assert dl.status_code == 200, dl.text
    assert dl.headers.get("content-type", "").startswith("text/plain")
    assert jd_line.encode() in dl.content or jd_line in dl.text

    alt_doc = {**doc, "heading": {"full_name": "Jane Doe — tailored"}}
    rp = client.put(
        f"/api/v1/variants/{vid}/document",
        headers=headers,
        json={"schema_version": "1", "document": alt_doc},
    )
    assert rp.status_code == 200, rp.text


def test_fork_jd_rejects_over_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JD_MAX_PLAINTEXT_CHARS", "10")
    get_settings.cache_clear()
    app = create_app()
    uid = str(uuid.uuid4())
    headers = {"x-user-id": uid}
    with TestClient(app) as client:
        rb = client.post(
            "/api/v1/bases",
            json={"title": "Cap base", "source": "guided"},
            headers=headers,
        )
        assert rb.status_code == 200, rb.text
        bid = str(rb.json()["id"])

        doc = json.loads((FIXTURES / "resume_minimal.json").read_text())
        rdoc = client.put(
            f"/api/v1/bases/{bid}/document",
            json={"schema_version": "1", "document": doc},
            headers=headers,
        )
        assert rdoc.status_code == 200, rdoc.text

        rf = client.post(
            f"/api/v1/bases/{bid}/variants",
            headers=headers,
            json={"jd_plaintext": "x" * 11},
        )
        assert rf.status_code == 413, rf.text
    get_settings.cache_clear()


def test_variant_thread_ensure(client: TestClient) -> None:
    uid = str(uuid.uuid4())
    headers = {"x-user-id": uid}

    rb = client.post(
        "/api/v1/bases",
        json={"title": "Variant thread base", "source": "guided"},
        headers=headers,
    )
    assert rb.status_code == 200, rb.text
    bid = str(rb.json()["id"])

    doc = json.loads((FIXTURES / "resume_minimal.json").read_text())
    rdoc = client.put(
        f"/api/v1/bases/{bid}/document",
        json={"schema_version": "1", "document": doc},
        headers=headers,
    )
    assert rdoc.status_code == 200, rdoc.text

    rv = client.post(f"/api/v1/bases/{bid}/variants", headers=headers, json={})
    assert rv.status_code == 201, rv.text
    vid = str(rv.json()["variant"]["id"])

    g404 = client.get(f"/api/v1/variants/{vid}/thread", headers=headers)
    assert g404.status_code == 404, g404.text

    po = client.post(f"/api/v1/variants/{vid}/thread", headers=headers)
    assert po.status_code == 200, po.text
    j = po.json()
    assert isinstance(j["langgraph_thread_id"], str)
    assert str(j["langgraph_thread_id"]).startswith("stub-web-var-")

    g2 = client.get(f"/api/v1/variants/{vid}/thread", headers=headers)
    assert g2.status_code == 200
    assert str(g2.json()["id"]) == str(j["id"])
