"""Extract plain text from PDF bytes (Phase 5.1).

Vision-based extraction is intentionally out of scope for v1; see :mod:`elena.import_path.vision_stub`.
"""

from __future__ import annotations

import io
import re


class EncryptedPdfError(Exception):
    """PDF uses encryption and cannot be opened without a password."""


def sniff_is_pdf(header: bytes) -> bool:
    return len(header) >= 5 and header[:5] == b"%PDF-"


_pdf_header_re = re.compile(rb"%PDF-(\d+)\.(\d+)")


def extract_text_pdf_bytes(data: bytes) -> tuple[str, int]:
    """Return *(full_text, page_count)* using pypdf.

    Raises :exc:`EncryptedPdfError` when a user password is required (password-protected file).
    PDFs encrypted only with an empty user password / owner-password-only are still readable
    via ``decrypt("")`` and are accepted.
    """

    try:
        from pypdf import PasswordType, PdfReader  # defer import for optional tooling
    except ImportError as e:
        raise RuntimeError("pypdf is required for PDF extraction") from e

    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted and reader.decrypt("") == PasswordType.NOT_DECRYPTED:
        raise EncryptedPdfError(
            "Password-protected PDFs cannot be imported — remove the password or export "
            "an unencrypted copy, then upload again.",
        )
    pages = len(reader.pages)
    chunks: list[str] = []
    for page in reader.pages:
        t = page.extract_text()
        chunks.append((t or "").strip())
    # Preserve page-ish boundaries lightly for heuristic sectioning
    text = "\n\n".join(c for c in chunks if c)
    return text, pages
