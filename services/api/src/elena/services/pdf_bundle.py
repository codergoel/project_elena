"""Result of compiling a stored résumé to a signed blob URL."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PdfRenderBundle:
    """PDF compile outcome + diagnostic tail surfaced to callers."""

    pdf_url: str
    compile_ok: bool
    page_count: int | None
    log_tail: str
    latex_user_hint: str | None
