"""Phase 6.1 deterministic guided slot transitions (unit, no HTTP)."""

from __future__ import annotations

from elena.guided_fsm import (
    apply_education,
    apply_experience,
    apply_heading_patch,
    apply_skills,
    bootstrap_envelope,
    next_pending_slot,
    parse_checkpoint,
    slot_is_done,
)
from elena.schemas.resume_document import EducationEntry


def test_bootstrap_placeholder_then_heading_advances_fsm() -> None:
    env = bootstrap_envelope()
    cp = parse_checkpoint(None)
    assert next_pending_slot(env.document, cp) == "heading"

    renamed = apply_heading_patch(env.document, full_name="Riley Chen")
    assert renamed.heading.full_name == "Riley Chen"
    assert slot_is_done("heading", renamed, cp)
    assert next_pending_slot(renamed, cp) == "education"


def test_skip_education_moves_to_experience() -> None:
    env = bootstrap_envelope()
    cp = parse_checkpoint(None)
    doc = apply_heading_patch(env.document, full_name="Riley Chen")

    skipped_doc, skipped_cp = apply_education(doc, cp=cp, skip=True, entry=None)

    assert "education" in skipped_cp.skipped
    assert next_pending_slot(skipped_doc, skipped_cp) == "experience"


def test_add_education_fills_slot() -> None:
    env = bootstrap_envelope()
    cp = parse_checkpoint(None)
    doc = apply_heading_patch(env.document, full_name="Riley Chen")

    edu = EducationEntry(
        institution="Test University",
        date_range="2020–2024",
        degree="B.S. CS",
        location="Boston, MA",
    )
    nd, ncp = apply_education(doc, cp=cp, skip=False, entry=edu)
    assert nd.education == [edu]
    assert slot_is_done("education", nd, ncp)


def test_terminal_after_all_skipped_or_done() -> None:
    env = bootstrap_envelope()
    cp = parse_checkpoint(None)
    doc = apply_heading_patch(env.document, full_name="Riley Chen")
    doc, cp = apply_education(doc, cp=cp, skip=True, entry=None)
    doc, cp = apply_experience(
        doc,
        cp=cp,
        skip=True,
        entry=None,
    )
    doc, cp = apply_skills(doc, cp=cp, skip=True, languages=None)
    assert next_pending_slot(doc, cp) is None
