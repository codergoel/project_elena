"""Escape user-controlled strings before embedding inside LaTeX arguments."""

from __future__ import annotations


def latex_escape_plain(text: str) -> str:
    """Minimal escaping for prose inside ``\\textbf``, ``\\resumeItem``, etc."""

    replacements: tuple[tuple[str, str], ...] = (
        ("\\", "\\textbackslash{}"),
        ("{", "\\{"),
        ("}", "\\}"),
        ("$", "\\$"),
        ("%", "\\%"),
        ("&", "\\&"),
        ("#", "\\#"),
        ("_", "\\_"),
        ("^", "\\textasciicircum{}"),
        ("~", "\\textasciitilde{}"),
    )
    escaped = text
    for src, repl in replacements:
        escaped = escaped.replace(src, repl)
    return escaped


def latex_url_for_href(url: str) -> str:
    """Escape literal URL fragment for hyperref ``\\href{first}{second}`` first arg."""

    return latex_escape_plain(url)
