"""Phase 6.1 guided intake slot order derived from docs/TEMPLATE_CONTRACT.md (minimal v1 spine)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

from elena.schemas.resume_document import (
    EducationEntry,
    ExperienceEntry,
    ResumeDocument,
    ResumeDocumentPayload,
    ResumeHeading,
    TechnicalSkills,
)
from elena.schemas.versioning import RESUME_SCHEMA_V1

GuidedSlotId = Literal["heading", "education", "experience", "skills"]

BOOTSTRAP_PLACEHOLDER_NAME = "Your name"

GUIDED_SLOT_ORDER: tuple[GuidedSlotId, ...] = ("heading", "education", "experience", "skills")

SLOT_PROMPTS: dict[str, str] = {
    "heading": (
        "Start with your heading: full name plus any contact lines you already know "
        "(email, phone, address — all optional)."
    ),
    "education": (
        "Add your strongest education block (school, degree, dates, location), or skip if you "
        "prefer to fill this later elsewhere."
    ),
    "experience": (
        "Add one flagship role (company, title, dates, location) and optional bullet accomplishments, or skip for now."
    ),
    "skills": (
        "Summarize technical skills as a comma-separated line (languages, stacks, tooling), "
        "or skip to finish the guided skeleton."
    ),
}


class GuidedCheckpoint(BaseModel):
    """Stored on ``base_resumes.guided_checkpoint`` for skips only (Phase 6.1)."""

    model_config = ConfigDict(extra="ignore")

    skipped: list[str] = Field(default_factory=list)


def parse_checkpoint(raw: dict | None) -> GuidedCheckpoint:
    if raw is None:
        return GuidedCheckpoint()
    return GuidedCheckpoint.model_validate(raw)


def bootstrap_envelope() -> ResumeDocumentPayload:
    doc = ResumeDocument(
        heading=ResumeHeading(full_name=BOOTSTRAP_PLACEHOLDER_NAME),
    )
    return ResumeDocumentPayload(schema_version=RESUME_SCHEMA_V1, document=doc)


def _heading_done(doc: ResumeDocument) -> bool:
    n = doc.heading.full_name.strip()
    return bool(n) and n.casefold() != BOOTSTRAP_PLACEHOLDER_NAME.casefold()


def _education_done(doc: ResumeDocument, cp: GuidedCheckpoint) -> bool:
    return "education" in cp.skipped or len(doc.education) >= 1


def _experience_done(doc: ResumeDocument, cp: GuidedCheckpoint) -> bool:
    return "experience" in cp.skipped or len(doc.experience) >= 1


def _skills_done(doc: ResumeDocument, cp: GuidedCheckpoint) -> bool:
    if "skills" in cp.skipped:
        return True
    ts = doc.technical_skills
    if ts is None:
        return False
    if ts.languages and str(ts.languages).strip():
        return True
    dev = ts.developer_tools and str(ts.developer_tools).strip()
    tech = ts.technologies_frameworks and str(ts.technologies_frameworks).strip()
    return bool(dev or tech)


def slot_is_done(slot: GuidedSlotId, doc: ResumeDocument, cp: GuidedCheckpoint) -> bool:
    if slot == "heading":
        return _heading_done(doc)
    if slot == "education":
        return _education_done(doc, cp)
    if slot == "experience":
        return _experience_done(doc, cp)
    return _skills_done(doc, cp)


def next_pending_slot(doc: ResumeDocument, cp: GuidedCheckpoint) -> GuidedSlotId | None:
    for sid in GUIDED_SLOT_ORDER:
        if not slot_is_done(sid, doc, cp):  # type: ignore[arg-type]
            return sid
    return None


def all_slots_complete(doc: ResumeDocument, cp: GuidedCheckpoint) -> bool:
    return next_pending_slot(doc, cp) is None


def ensure_skip(cp: GuidedCheckpoint, slot: str) -> GuidedCheckpoint:
    uniq = sorted({*cp.skipped, slot})
    return GuidedCheckpoint(skipped=uniq)


def apply_heading_patch(
    doc: ResumeDocument,
    *,
    full_name: str,
    email: EmailStr | None = None,
    phone: str | None = None,
    address_line: str | None = None,
    linkedin_url: HttpUrl | None = None,
    github_url: HttpUrl | None = None,
) -> ResumeDocument:
    h = ResumeHeading(
        full_name=full_name,
        email=email or doc.heading.email,
        phone=(phone.strip() if phone else None) or doc.heading.phone,
        address_line=(address_line.strip() if address_line else None) or doc.heading.address_line,
        linkedin_url=linkedin_url or doc.heading.linkedin_url,
        github_url=github_url or doc.heading.github_url,
    )
    return doc.model_copy(update={"heading": h})


def apply_education(
    doc: ResumeDocument,
    *,
    cp: GuidedCheckpoint,
    skip: bool,
    entry: EducationEntry | None = None,
) -> tuple[ResumeDocument, GuidedCheckpoint]:
    if skip:
        return doc, ensure_skip(cp, "education")
    if entry is None:
        raise ValueError("education entry required when skip is False")
    return doc.model_copy(update={"education": [*doc.education, entry]}), cp


def apply_experience(
    doc: ResumeDocument,
    *,
    cp: GuidedCheckpoint,
    skip: bool,
    entry: ExperienceEntry | None = None,
) -> tuple[ResumeDocument, GuidedCheckpoint]:
    if skip:
        return doc, ensure_skip(cp, "experience")
    if entry is None:
        raise ValueError("experience entry required when skip is False")
    return doc.model_copy(update={"experience": [*doc.experience, entry]}), cp


def apply_skills(
    doc: ResumeDocument,
    *,
    cp: GuidedCheckpoint,
    skip: bool,
    languages: str | None = None,
) -> tuple[ResumeDocument, GuidedCheckpoint]:
    if skip:
        return doc, ensure_skip(cp, "skills")
    langs = (languages or "").strip()
    if not langs:
        raise ValueError("languages line required unless skip=True")
    ts = TechnicalSkills(languages=langs, developer_tools=None, technologies_frameworks=None)
    return doc.model_copy(update={"technical_skills": ts}), cp
