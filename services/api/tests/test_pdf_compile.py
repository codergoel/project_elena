"""Golden PDF compile (requires pdflatex on PATH)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from elena.rendering.compiler import compile_resume_tex
from elena.rendering.tex_builder import resume_document_to_tex
from elena.schemas import parse_resume_document

FIXTURES = Path(__file__).resolve().parent / "fixtures"

pytestmark = pytest.mark.latex


@pytest.mark.asyncio
async def test_resume_minimal_compiles_to_pdf_magic() -> None:
    raw = json.loads((FIXTURES / "resume_minimal.json").read_text())
    doc = parse_resume_document(raw)
    tex = resume_document_to_tex(doc)
    result = await compile_resume_tex(tex, timeout_seconds=120.0)
    assert result.pdf_bytes is not None
    assert result.pdf_bytes.startswith(b"%PDF")
    assert result.ok is True
