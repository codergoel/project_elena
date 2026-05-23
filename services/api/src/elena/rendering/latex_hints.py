"""Best-effort LaTeX error surfacing for API clients (Phase 9.2)."""

from __future__ import annotations

import re

_MAX_HINT = 600
_ERR_LINE_RE = re.compile(r"^! .*$")


def latex_compile_user_hint(log_tail: str) -> str | None:
    """Pull a concise line users can grep or paste to support."""

    text = log_tail.strip()
    if not text:
        return None

    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if _ERR_LINE_RE.match(s):
            return s[:_MAX_HINT]
        if "LaTeX Error:" in s or "Emergency stop." in s or "fatal error" in s.lower():
            return s[:_MAX_HINT]

    return None
