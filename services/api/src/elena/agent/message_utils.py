"""Helpers to interpret LangGraph message lists for HTTP responses."""

from __future__ import annotations

import json
from typing import Any


def assistant_final_text(messages: list[Any]) -> str:
    """Return the newest non-empty AI text chunk if present."""

    from langchain_core.messages import AIMessage

    for m in reversed(messages):
        if isinstance(m, AIMessage):
            text = _stringify_ai_content(m.content)
            if text.strip():
                return text.strip()
    return ""


def _stringify_ai_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content or "")


def last_render_pdf_tool_url(messages: list[Any]) -> str | None:
    """If ``render_resume_pdf`` returned JSON with pdf_url, surface it."""

    from langchain_core.messages import ToolMessage

    for m in reversed(messages):
        if not isinstance(m, ToolMessage):
            continue
        if getattr(m, "name", "") != "render_resume_pdf":
            continue
        try:
            parsed = json.loads(str(m.content))
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and parsed.get("ok"):
            url = parsed.get("pdf_url")
            if isinstance(url, str) and url.startswith("http"):
                return url

    return None
