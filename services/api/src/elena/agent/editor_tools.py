"""LangGraph tools: read/write ``ResumeDocument`` and compile PDF (Phase 7.3)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from langchain_core.tools import tool
from pydantic import ValidationError
from sqlalchemy import select

from elena.agent.tool_context import CURRENT_AGENT_CTX, AgentToolContext
from elena.api.quota import enforce_compile_budget
from elena.db.models import BaseResume as BaseResumeRow
from elena.db.models import StoredResumeDocument
from elena.db.models import Variant as VariantRow
from elena.schemas.resume_document import ResumeDocumentPayload
from elena.services.render_pdf import pdf_url_from_stored_row


def _ctx() -> AgentToolContext | None:
    return CURRENT_AGENT_CTX.get()


def _missing() -> str:
    return json.dumps({"ok": False, "error": "agent_tool_context_missing"})


@tool(parse_docstring=False)
async def get_resume_json() -> str:
    """Fetch the active résumé as JSON envelope {schema_version, document} for this editing context."""

    ctx = _ctx()
    if ctx is None:
        return _missing()

    if ctx.mode == "base":
        res_q = await ctx.session.execute(select(BaseResumeRow).where(BaseResumeRow.id == ctx.record_id))
        row = res_q.scalar_one_or_none()
        if row is None:
            return json.dumps({"ok": False, "error": "base_not_found"})
        active_id = row.active_document_id
    else:
        res_q = await ctx.session.execute(select(VariantRow).where(VariantRow.id == ctx.record_id))
        row = res_q.scalar_one_or_none()
        if row is None:
            return json.dumps({"ok": False, "error": "variant_not_found"})
        active_id = row.active_document_id

    if active_id is None:
        return json.dumps({"ok": False, "error": "no_active_document"})

    doc_q = await ctx.session.execute(select(StoredResumeDocument).where(StoredResumeDocument.id == active_id))
    doc = doc_q.scalar_one_or_none()
    if doc is None:
        return json.dumps({"ok": False, "error": "document_row_missing"})

    env = {"schema_version": doc.schema_version, "document": doc.payload}
    return json.dumps({"ok": True, "envelope": env}, default=str)


@tool(parse_docstring=False)
async def put_resume_json(envelope_json: str) -> str:
    """Replace the active résumé from a full JSON envelope: {\"schema_version\": \"1\", \"document\": {...}}."""

    ctx = _ctx()
    if ctx is None:
        return _missing()

    try:
        raw = json.loads(envelope_json)
    except json.JSONDecodeError as exc:
        return json.dumps({"ok": False, "error": f"invalid_json: {exc!s}"})

    try:
        env = ResumeDocumentPayload.model_validate(raw)
    except ValidationError as exc:
        return json.dumps({"ok": False, "error": f"schema_error: {exc!s}"})

    doc_dict = env.document.model_dump(mode="json")
    rd = StoredResumeDocument(
        id=uuid.uuid4(),
        schema_version=str(env.schema_version),
        payload=doc_dict,
        forked_from_id=None,
    )
    ctx.session.add(rd)
    await ctx.session.flush()

    now = datetime.now(UTC)
    if ctx.mode == "base":
        bq = await ctx.session.execute(select(BaseResumeRow).where(BaseResumeRow.id == ctx.record_id))
        base = bq.scalar_one_or_none()
        if base is None:
            return json.dumps({"ok": False, "error": "base_not_found"})
        base.active_document_id = rd.id
        base.updated_at = now
        ctx.session.add(base)
    else:
        vq = await ctx.session.execute(select(VariantRow).where(VariantRow.id == ctx.record_id))
        variant = vq.scalar_one_or_none()
        if variant is None:
            return json.dumps({"ok": False, "error": "variant_not_found"})
        variant.active_document_id = rd.id
        variant.updated_at = now
        ctx.session.add(variant)

    await ctx.session.commit()
    return json.dumps({"ok": True, "stored_document_id": str(rd.id)})


@tool(parse_docstring=False)
async def render_resume_pdf() -> str:
    """Compile the active résumé to PDF; returns JSON with pdf_url, compile_ok, log_tail excerpt."""

    ctx = _ctx()
    if ctx is None:
        return _missing()

    if ctx.mode == "base":
        res_q = await ctx.session.execute(select(BaseResumeRow).where(BaseResumeRow.id == ctx.record_id))
        row = res_q.scalar_one_or_none()
        if row is None:
            return json.dumps({"ok": False, "error": "base_not_found"})
        sid = row.active_document_id
    else:
        res_q = await ctx.session.execute(select(VariantRow).where(VariantRow.id == ctx.record_id))
        row = res_q.scalar_one_or_none()
        if row is None:
            return json.dumps({"ok": False, "error": "variant_not_found"})
        sid = row.active_document_id

    if sid is None:
        return json.dumps({"ok": False, "error": "no_active_document"})

    await enforce_compile_budget(
        ctx.redis,
        limit=ctx.settings.compile_quota_per_minute_per_user,
        user_id_key=str(ctx.user_id),
    )

    try:
        bundle = await pdf_url_from_stored_row(
            ctx.session,
            ctx.blobs,
            stored_id=sid,
            owning_user_id=ctx.user_id,
            settings=ctx.settings,
        )
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"ok": False, "compile_ok": False, "error": str(exc)[:2000]})

    return json.dumps(
        {
            "ok": True,
            "compile_ok": bundle.compile_ok,
            "pdf_url": bundle.pdf_url,
            "page_count": bundle.page_count,
            "log_tail": bundle.log_tail[:4000],
            "latex_user_hint": bundle.latex_user_hint,
        },
    )
