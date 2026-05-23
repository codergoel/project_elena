"""In-template résumé JSON (ResumeDocument).

Field names and cardinality match docs/TEMPLATE_CONTRACT.md §3.1–§3.7.

Contract audit (field names ↔ contract):
  §3.1 ResumeHeading — full_name (req), address_line, phone, email, linkedin_url,
       github_url
  §3.2 EducationEntry — institution, date_range, degree, location
  §3.3 RelevantCoursework — courses
  §3.4 ExperienceEntry — organization, date_range, title, location, bullets
  §3.5 ProjectEntry — name (req), tech_stack, date, bullets
  §3.6 TechnicalSkills — languages, developer_tools, technologies_frameworks
  §3.7 leadership_extracurricular — list[ExperienceEntry] (same as §3.4)

Section order for renderers: elena.schemas.versioning.RESUME_SECTION_ORDER (§2).

Empty-section policy: lists default to []. Optional block objects use None to mean
"omit this block"; the LaTeX renderer should omit empty sections in the PDF (see
TEMPLATE_CONTRACT.md §7 implementation checklist).

Out-of-template content (photo, summary, certifications, etc.) must NOT appear here;
store it on UserProfile per TEMPLATE_CONTRACT.md §5–§6.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

from elena.schemas.versioning import RESUME_SCHEMA_V1, ResumeSchemaVersionV1


class ResumeHeading(BaseModel):
    """TEMPLATE_CONTRACT.md §3.1."""

    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1)
    address_line: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    linkedin_url: HttpUrl | None = None
    github_url: HttpUrl | None = None


class EducationEntry(BaseModel):
    """TEMPLATE_CONTRACT.md §3.2."""

    model_config = ConfigDict(extra="forbid")

    institution: str = Field(min_length=1)
    date_range: str = Field(min_length=1)
    degree: str = Field(min_length=1)
    location: str = Field(min_length=1)


class RelevantCoursework(BaseModel):
    """TEMPLATE_CONTRACT.md §3.3."""

    model_config = ConfigDict(extra="forbid")

    courses: list[str] = Field(default_factory=list)


class ExperienceEntry(BaseModel):
    """TEMPLATE_CONTRACT.md §3.4 and §3.7 (Leadership / Extracurricular)."""

    model_config = ConfigDict(extra="forbid")

    organization: str = Field(min_length=1)
    date_range: str = Field(min_length=1)
    title: str = Field(min_length=1)
    location: str = Field(min_length=1)
    bullets: list[str] = Field(default_factory=list)


class ProjectEntry(BaseModel):
    """TEMPLATE_CONTRACT.md §3.5."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    tech_stack: str | None = None
    date: str | None = None
    bullets: list[str] = Field(default_factory=list)


class TechnicalSkills(BaseModel):
    """TEMPLATE_CONTRACT.md §3.6."""

    model_config = ConfigDict(extra="forbid")

    languages: str | None = None
    developer_tools: str | None = None
    technologies_frameworks: str | None = None


class ResumeDocument(BaseModel):
    """Canonical structured payload that renders to the Jake v1 template."""

    model_config = ConfigDict(extra="forbid")

    heading: ResumeHeading
    education: list[EducationEntry] = Field(default_factory=list)
    relevant_coursework: RelevantCoursework | None = None
    experience: list[ExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    technical_skills: TechnicalSkills | None = None
    leadership_extracurricular: list[ExperienceEntry] = Field(default_factory=list)


class ResumeDocumentPayload(BaseModel):
    """Envelope for DB `payload` + `schema_version` (docs/VERSIONING_MODEL.md §5)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: ResumeSchemaVersionV1 = Field(default=RESUME_SCHEMA_V1)
    document: ResumeDocument
