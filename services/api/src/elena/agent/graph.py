"""Build the LangGraph Résumé editor ReAct agent (Gemini + tools + Postgres checkpoints)."""

from __future__ import annotations

from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.prebuilt import create_react_agent

from elena.agent.editor_tools import get_resume_json, put_resume_json, render_resume_pdf
from elena.config import Settings

_AGENT_SYSTEM_PROMPT = """You are Elena, a meticulous résumé editor assistant.
You help revise a Jake-template résumé JSON for this workspace.

Rules:
- Never invent employers, degrees, certifications, or jobs that are not in the user's message or snapshot.
- Decline politely if asked to fabricate achievements; steer the user toward truthful wording grounded in snapshot data.
- Always call ``get_resume_json`` before proposing structured edits unless the user pasted fresh JSON you should apply.
- To save structured changes, pass the **full** validated envelope JSON string to ``put_resume_json``.
- Offer ``render_resume_pdf`` after substantive edits when a PDF preview matters.
- Prefer concise confirmations; cite which sections changed."""


def compile_resume_editor_agent(
    *,
    settings: Settings,
    checkpointer: BaseCheckpointSaver,
) -> Any:
    """Return a compiled LangGraph runnable for one chat turn."""

    key = (settings.gemini_api_key or "").strip()
    if not key:
        msg = "compile_resume_editor_agent requires GEMINI_API_KEY"
        raise ValueError(msg)

    model_name = (settings.gemini_model or "gemini-3.5-flash").strip()
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=key,
    )

    return create_react_agent(
        llm,
        tools=[get_resume_json, put_resume_json, render_resume_pdf],
        checkpointer=checkpointer,
        prompt=_AGENT_SYSTEM_PROMPT,
    )
