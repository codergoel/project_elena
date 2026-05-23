"""Résumé editor agent (Gemini via LangGraph, Phase 7.3 — non-streaming)."""

from __future__ import annotations

import time
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from langchain_core.messages import HumanMessage

from elena.access import owned_base, owned_variant
from elena.agent.message_utils import assistant_final_text, last_render_pdf_tool_url
from elena.agent.tool_context import CURRENT_AGENT_CTX, AgentToolContext
from elena.api.deps import BlobStoreDep, RedisDep, SessionDep, SettingsDep, UserIdDep
from elena.api.dto import AgentTurnBody, AgentTurnResponse
from elena.api.quota import enforce_minute_budget
from elena.config import Settings
from elena.conversation.threads import ensure_thread_for_base, ensure_thread_for_variant
from elena.observability.metrics import observe_agent_turn_outcome

router = APIRouter(tags=["agent"])


def get_resume_editor_graph(request: Request) -> Any:
    graph = getattr(request.app.state, "agent_graph", None)
    if graph is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Editor agent is not available. Set GEMINI_API_KEY on the API and restart so "
                "LangGraph checkpoints can initialise."
            ),
        )
    return graph


GraphDep = Annotated[Any, Depends(get_resume_editor_graph)]


async def _run_turn(
    *,
    settings: Settings,
    session_uuid: uuid.UUID,
    redis: RedisDep,
    blobs: BlobStoreDep,
    user_id: uuid.UUID,
    tool_ctx: AgentToolContext,
    graph: Any,
    message: str,
) -> AgentTurnResponse:
    await enforce_minute_budget(
        redis,
        scope="agent_turn",
        limit=settings.agent_turn_quota_per_minute_per_user,
        user_id_key=str(user_id),
    )

    cfg = {"configurable": {"thread_id": str(session_uuid)}}

    tok = CURRENT_AGENT_CTX.set(tool_ctx)
    wall_t0 = time.perf_counter()
    try:
        out = await graph.ainvoke({"messages": [HumanMessage(content=message.strip())]}, config=cfg)
    except Exception:
        observe_agent_turn_outcome("graph_exception", time.perf_counter() - wall_t0)
        await tool_ctx.session.rollback()
        raise
    finally:
        CURRENT_AGENT_CTX.reset(tok)
    observe_agent_turn_outcome("success", time.perf_counter() - wall_t0)

    msgs = out.get("messages", [])
    return AgentTurnResponse(
        assistant=assistant_final_text(msgs),
        thread_id=session_uuid,
        last_pdf_url=last_render_pdf_tool_url(msgs),
    )


@router.post("/bases/{base_id}/agent/turn", response_model=AgentTurnResponse)
async def agent_turn_base_resume(
    base_id: uuid.UUID,
    body: AgentTurnBody,
    request: Request,
    session: SessionDep,
    user_id: UserIdDep,
    settings: SettingsDep,
    redis: RedisDep,
    blobs: BlobStoreDep,
    graph: GraphDep,
) -> AgentTurnResponse:
    del request
    await owned_base(session, user_id, base_id)
    ct = await ensure_thread_for_base(session, base_resume_id=base_id)
    ctx = AgentToolContext(
        session=session,
        user_id=user_id,
        mode="base",
        record_id=base_id,
        blobs=blobs,
        settings=settings,
        redis=redis,
    )
    return await _run_turn(
        settings=settings,
        session_uuid=ct.id,
        redis=redis,
        blobs=blobs,
        user_id=user_id,
        tool_ctx=ctx,
        graph=graph,
        message=body.message,
    )


@router.post("/variants/{variant_id}/agent/turn", response_model=AgentTurnResponse)
async def agent_turn_variant(
    variant_id: uuid.UUID,
    body: AgentTurnBody,
    request: Request,
    session: SessionDep,
    user_id: UserIdDep,
    settings: SettingsDep,
    redis: RedisDep,
    blobs: BlobStoreDep,
    graph: GraphDep,
) -> AgentTurnResponse:
    del request
    await owned_variant(session, user_id, variant_id)
    ct = await ensure_thread_for_variant(session, variant_id=variant_id)
    ctx = AgentToolContext(
        session=session,
        user_id=user_id,
        mode="variant",
        record_id=variant_id,
        blobs=blobs,
        settings=settings,
        redis=redis,
    )
    return await _run_turn(
        settings=settings,
        session_uuid=ct.id,
        redis=redis,
        blobs=blobs,
        user_id=user_id,
        tool_ctx=ctx,
        graph=graph,
        message=body.message,
    )
