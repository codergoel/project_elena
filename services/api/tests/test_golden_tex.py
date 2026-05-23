"""Deterministic excerpts from Résumé → LaTeX (no pdflatex)."""

from __future__ import annotations

import json
from pathlib import Path

from elena.rendering.tex_builder import build_body_tex, resume_document_to_tex
from elena.schemas import parse_resume_document

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_minimal_heading_contains_name_and_typography_macros() -> None:
    raw = json.loads((FIXTURES / "resume_minimal.json").read_text())
    doc = parse_resume_document(raw)
    body = build_body_tex(doc)
    assert "\\Huge \\scshape" in body
    assert "Jane Doe" in body
    tex = resume_document_to_tex(doc)
    assert "\\pdfgentounicode=1" in tex
    assert "\\begin{document}" in tex
    assert "\\usepackage{fontawesome5}" in tex
