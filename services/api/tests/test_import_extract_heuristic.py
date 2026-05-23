"""Unit tests for PDF sniff/extract + heuristic mapper (Phase 5, no Redis/Postgres)."""

from __future__ import annotations

import io

import pytest
from pypdf import PdfWriter
from reportlab.pdfgen import canvas

from elena.import_path.extract_pdf import EncryptedPdfError, extract_text_pdf_bytes, sniff_is_pdf
from elena.import_path.heuristic_mapper import heuristic_map_plaintext


def _sample_pdf_bytes(lines: tuple[str, ...]) -> bytes:
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf)
    y = 800
    for line in lines:
        pdf.drawString(72, y, line[:500])
        y -= 22
        if y < 80:
            break
    pdf.showPage()
    pdf.save()
    return buf.getvalue()


def test_sniff_and_extract_plain_pdf() -> None:
    blob = _sample_pdf_bytes(("Alex Rivera", "alex@media.org"))
    assert sniff_is_pdf(blob[:8])
    text, pages = extract_text_pdf_bytes(blob)
    assert pages >= 1
    assert "Alex Rivera" in text
    assert "alex@media.org" in text


def test_extract_rejects_user_password_pdf() -> None:
    buf = io.BytesIO()
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    w.encrypt("user-secret-password-not-empty")
    w.write(buf)

    with pytest.raises(EncryptedPdfError, match="Password-protected"):
        extract_text_pdf_bytes(buf.getvalue())


@pytest.mark.parametrize(
    ("text", "expect_substr"),
    [
        (
            """Jordan Lee\njordan@example.net\nlinkedin.com/in/jordan\n""",
            "jordan@example.net",
        ),
        (
            """Casey Doe\ncasey@github-demo.org\nExperience\n- Owned payments\n""",
            "payments",
        ),
    ],
)
def test_heuristic_maps_email_or_bullets(text: str, expect_substr: str) -> None:
    result = heuristic_map_plaintext(text)
    dumped = result.envelope.document.model_dump_json()
    assert expect_substr in dumped
    assert 0 <= result.overall_confidence <= 1.0


def test_heuristic_always_has_overflow_review_text() -> None:
    blob = "".join(f"Line {i} filler text\n" for i in range(30))
    result = heuristic_map_plaintext(blob)
    assert result.user_profile.overflow_sections
    excerpt = result.user_profile.overflow_sections[0].raw_text or ""
    assert len(excerpt) > 0
