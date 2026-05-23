"""LLM-backed import mapping — Gemini REST or OpenAI-compatible ``/chat/completions`` (Phase 5.2)."""

from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import HTTPException, status
from pydantic import ValidationError

from elena.config import Settings
from elena.import_path.heuristic_mapper import ImportMappingResult
from elena.observability.metrics import observe_import_llm_outcome
from elena.schemas.parse import parse_resume_document_payload, parse_user_profile
from elena.schemas.user_profile import UserProfile

_SYSTEM = """You extract structured résumé data for the Elena app.
Return ONLY valid JSON (no markdown fences) with keys:
- schema_version: string, use "1"
- document: ResumeDocument-shaped object (field names described in user message).
- user_profile: overflow_sections (list) and extensions (object). Put unmapped text in overflow_sections
   items with title, optional raw_text and structured payloads.
- field_confidence: object mapping dotted paths (e.g. "heading.full_name", "experience.0.organization") to floats 0..1.

Rules:
- Never invent employers, degrees, or employers you cannot infer from the text.
- If unsure, use placeholders like "(review)" and low confidence.
- Keep LinkedIn/GitHub URLs only if present in the source text.
"""

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _gemini_generation_config(settings: Settings) -> dict[str, Any]:
    """Gemini 3.x prefers JSON-focused config without legacy temperature/top‑p knobs."""

    model = (settings.gemini_model or "").strip().lower()
    gc: dict[str, Any] = {"responseMimeType": "application/json"}
    if model.startswith("gemini-3"):
        gc["maxOutputTokens"] = 8192
        return gc
    gc["temperature"] = 0.1
    return gc


def _user_message(raw_text: str, settings: Settings) -> str:
    return (
        "TEXT TO PARSE:\n\n"
        f"{raw_text[: settings.import_max_extracted_chars]}\n\n"
        "ResumeDocument JSON fields: heading{full_name,address_line,phone,email,linkedin_url,github_url}, "
        "education[], relevant_coursework{courses}, experience[], projects[], "
        "technical_skills{languages,developer_tools,technologies_frameworks}, "
        "leadership_extracurricular[]."
    )


def _result_from_parsed_mapping(payload: dict) -> ImportMappingResult:
    """Validate LLM JSON object into structured import result."""

    document_raw = payload.get("document")
    if document_raw is None and isinstance(payload.get("resume"), dict):
        document_raw = payload.get("resume")
    if not isinstance(document_raw, dict):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='LLM JSON must include object key "document"',
        )

    try:
        envelope = parse_resume_document_payload({"schema_version": "1", "document": document_raw})
    except ValidationError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"LLM JSON failed ResumeDocument validation: {exc}",
        ) from exc

    try:
        prof_raw = payload.get("user_profile") or {"overflow_sections": [], "extensions": {}}
        profile = parse_user_profile(prof_raw if isinstance(prof_raw, dict) else {})
    except ValidationError as exc:
        profile = UserProfile(
            overflow_sections=[],
            extensions={"profile_parse_error": str(exc)[:2000]},
        )

    fc_raw = payload.get("field_confidence") or {}
    field_confidence: dict[str, float] = {}
    if isinstance(fc_raw, dict):
        for k, v in fc_raw.items():
            try:
                field_confidence[str(k)] = float(v)
            except (TypeError, ValueError):
                continue

    if not field_confidence:
        field_confidence["llm.mapping"] = 0.75

    overall = sum(field_confidence.values()) / max(1, len(field_confidence)) if field_confidence else 0.75

    return ImportMappingResult(
        envelope=envelope,
        user_profile=profile,
        field_confidence=field_confidence,
        overall_confidence=overall,
    )


def _gemini_extract_text(api_json: dict) -> str:
    blocks = []
    last_reason = None
    for cand in api_json.get("candidates") or []:
        if not isinstance(cand, dict):
            continue
        last_reason = cand.get("finishReason")
        for p in (cand.get("content") or {}).get("parts") or []:
            if not isinstance(p, dict):
                continue
            t = p.get("text")
            if isinstance(t, str):
                blocks.append(t)

    pb = api_json.get("promptFeedback") if isinstance(api_json, dict) else None
    blocked = pb.get("blockReason") if isinstance(pb, dict) else None

    text = "".join(blocks).strip()
    if text:
        return text

    parts = ["No usable text from Gemini."]
    if last_reason:
        parts.append(f"finishReason={last_reason}")
    if blocked:
        parts.append(f"promptBlock={blocked}")
    raise HTTPException(
        status.HTTP_502_BAD_GATEWAY,
        detail=" ".join(parts),
    )


async def _gemini_map_plaintext(raw_text: str, settings: Settings) -> ImportMappingResult:
    key = (settings.gemini_api_key or "").strip()
    if not key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY is not set",
        )
    model = (settings.gemini_model or "gemini-3.5-flash").strip()

    url = f"{_GEMINI_BASE}/models/{model}:generateContent"
    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": _SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": _user_message(raw_text, settings)}]}],
        "generationConfig": _gemini_generation_config(settings),
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, params={"key": key}, json=body)

    if resp.status_code >= 400:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini error: {resp.status_code} {resp.text[:800]}",
        )

    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Gemini returned non-JSON body",
        ) from exc

    content_str = _gemini_extract_text(data if isinstance(data, dict) else {})

    try:
        payload = json.loads(content_str)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini did not return JSON: {exc!s}",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="Gemini JSON must be an object")

    return _result_from_parsed_mapping(payload)


async def _openai_compatible_map_plaintext(raw_text: str, settings: Settings) -> ImportMappingResult:
    base = (settings.llm_api_base_url or "").rstrip("/")
    url = f"{base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    body: dict[str, Any] = {
        "model": settings.llm_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _user_message(raw_text, settings)},
        ],
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, headers=headers, json=body)
    if resp.status_code >= 400:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM provider error: {resp.status_code} {resp.text[:800]}",
        )

    data = resp.json()
    content = ""
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected LLM response shape",
        ) from exc

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM did not return JSON: {exc!s}",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="LLM JSON must be an object",
        )

    return _result_from_parsed_mapping(payload)


async def llm_map_plaintext(raw_text: str, settings: Settings) -> ImportMappingResult:
    """Prefer Gemini API when ``GEMINI_API_KEY`` is set; otherwise OpenAI-compatible chat."""

    gemini_key = (settings.gemini_api_key or "").strip()
    try:
        if gemini_key:
            result = await _gemini_map_plaintext(raw_text, settings)
        elif not settings.llm_api_key or not settings.llm_api_base_url:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=("LLM import is not configured: set GEMINI_API_KEY or LLM_API_BASE_URL + LLM_API_KEY"),
            )
        else:
            result = await _openai_compatible_map_plaintext(raw_text, settings)
    except Exception:
        observe_import_llm_outcome("failure")
        raise
    observe_import_llm_outcome("success")
    return result
