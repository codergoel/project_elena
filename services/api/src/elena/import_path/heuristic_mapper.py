"""Heuristic plaintext → structured résumé (Phase 5.2 deterministic path)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import HttpUrl, TypeAdapter, ValidationError

from elena.schemas.resume_document import (
    EducationEntry,
    ExperienceEntry,
    ResumeDocument,
    ResumeDocumentPayload,
    ResumeHeading,
    TechnicalSkills,
)
from elena.schemas.user_profile import OverflowSection, UserProfile

_CONF_STRONG = 0.92
_CONF_MED = 0.68
_CONF_WEAK = 0.42

_email_re = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_linkedin_re = re.compile(r"(https?://(?:www\.)?linkedin\.com/[^\s)]+)")
_github_re = re.compile(r"(https?://(?:www\.)?github\.com/[^\s)]+)")
_bullet_re = re.compile(r"^\s*(?:[\-\*\u2022•]|\d+[\).\]])\s+(.+)$")
_section_re = re.compile(r"(?i)^(experience|education|projects?|skills?|technical\s+skills|leadership)\b[^\n]*$")


@dataclass(frozen=True)
class ImportMappingResult:
    envelope: ResumeDocumentPayload
    user_profile: UserProfile
    field_confidence: dict[str, float]
    overall_confidence: float


def heuristic_map_plaintext(text: str) -> ImportMappingResult:
    flat = "\n".join(line.rstrip() for line in text.splitlines())
    lines_non_empty = [ln.strip() for ln in flat.splitlines() if ln.strip()]

    field_confidence: dict[str, float] = {}

    emails = _email_re.findall(flat)
    email = None
    if emails:
        try:
            from pydantic import EmailStr

            email = TypeAdapter(EmailStr).validate_python(emails[0])
        except ValidationError:
            email = None
        field_confidence["heading.email"] = _CONF_STRONG if email else _CONF_WEAK

    ln_m = _linkedin_re.search(flat)
    gh_m = _github_re.search(flat)
    linkedin = _http_or_none(ln_m.group(1) if ln_m else None)
    github = _http_or_none(gh_m.group(1) if gh_m else None)

    name = "Imported candidate"
    name_score = _CONF_WEAK
    if lines_non_empty:
        cand = lines_non_empty[0]
        if "@" not in cand and len(cand) < 96 and not cand.startswith("http") and not _section_re.match(cand):
            name = cand
            name_score = _CONF_MED
    field_confidence["heading.full_name"] = name_score

    heading = ResumeHeading(
        full_name=name,
        email=email,
        linkedin_url=linkedin,
        github_url=github,
    )

    bullets: list[str] = []
    misc_lines: list[str] = []
    for ln in lines_non_empty[1:]:
        if _section_re.match(ln):
            continue
        mb = _bullet_re.match(ln)
        if mb:
            bullets.append(mb.group(1).strip())
            field_confidence.setdefault("experience.bullet_parsed", _CONF_MED)
            continue
        if len(ln) > 2:
            misc_lines.append(ln)

    experience_rows: list[ExperienceEntry] = []
    if bullets:
        experience_rows.append(
            ExperienceEntry(
                organization="Imported experience — please review employers",
                date_range="(review)",
                title="Imported from PDF text",
                location="—",
                bullets=bullets[:24],
            ),
        )
        field_confidence["experience.block"] = _CONF_WEAK
    elif misc_lines[:5]:
        experience_rows.append(
            ExperienceEntry(
                organization="Unstructured paragraphs — review manually",
                date_range="(review)",
                title="Imported text",
                location="—",
                bullets=[" ".join(misc_lines[:5])[:900]],
            ),
        )
        field_confidence["experience.fallback_blob"] = _CONF_WEAK

    education_entries: list[EducationEntry] = []
    uni_like = [
        ln for ln in misc_lines[:20] if re.search(r"(?i)\b(university|college|institute)\b", ln) and len(ln) < 200
    ]
    i = 0
    for u in uni_like[:3]:
        education_entries.append(
            EducationEntry(
                institution=u,
                date_range="(review)",
                degree="Degree / major (review)",
                location="—",
            ),
        )
        field_confidence[f"education.{i}.line"] = _CONF_WEAK
        i += 1

    skills_line = ",".join(
        token.strip()
        for token in misc_lines
        if re.search(r"(?i)\b(java|python|typescript|javascript|rust|react|docker|kubernetes|sql|c\+\+)\b", token)
    )[:520]
    technical = (
        TechnicalSkills(languages=skills_line, developer_tools=None, technologies_frameworks=None)
        if skills_line
        else None
    )
    if technical:
        field_confidence["technical_skills.languages_heuristic"] = _CONF_WEAK

    envelope = ResumeDocumentPayload(
        document=ResumeDocument(
            heading=heading,
            education=education_entries,
            relevant_coursework=None,
            experience=experience_rows,
            projects=[],
            technical_skills=technical,
            leadership_extracurricular=[],
        ),
    )

    overflow_suffix = "\n".join(lines_non_empty[-40:]) if len(lines_non_empty) > 15 else ""
    profile = UserProfile(
        overflow_sections=[
            OverflowSection(
                unmapped_section_title="Import source excerpt (review)",
                raw_text=flat[:120_000],
                structured={"tail_preview": overflow_suffix[:8000]} if overflow_suffix else {},
            ),
        ],
        extensions={"mapper": "heuristic_v1"},
    )

    overall = sum(field_confidence.values()) / max(1, len(field_confidence)) if field_confidence else _CONF_WEAK

    envelope.model_validate(envelope.model_dump(mode="json"))
    profile.model_validate(profile.model_dump(mode="json"))

    return ImportMappingResult(
        envelope=envelope,
        user_profile=profile,
        field_confidence=field_confidence,
        overall_confidence=overall,
    )


def _http_or_none(url: str | None) -> HttpUrl | None:
    if url is None:
        return None
    try:
        return HttpUrl(url)
    except ValidationError:
        return None
