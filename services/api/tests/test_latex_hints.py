"""Compile log hint extraction."""

from __future__ import annotations

from elena.rendering.latex_hints import latex_compile_user_hint


def test_latex_compile_user_hint_picks_bang_line() -> None:
    tail = "some noise\n! LaTeX Error: Undefined control sequence.\nmore"
    assert latex_compile_user_hint(tail) == "! LaTeX Error: Undefined control sequence."


def test_latex_compile_user_hint_finds_latex_error_inline() -> None:
    tail = "foo\nSomething went wrong: LaTeX Error: Missing \\begin{document}.\nbar"
    h = latex_compile_user_hint(tail)
    assert h is not None
    assert "LaTeX Error" in h


def test_latex_compile_user_hint_empty_returns_none() -> None:
    assert latex_compile_user_hint("") is None
    assert latex_compile_user_hint("   ") is None
