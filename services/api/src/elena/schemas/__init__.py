"""Validated JSON schemas for résumé payload and user overflow profile.

Canonical field definitions: docs/TEMPLATE_CONTRACT.md.
Versioning semantics: docs/VERSIONING_MODEL.md.
"""

from elena.schemas.parse import (
    parse_resume_document,
    parse_resume_document_payload,
    parse_user_profile,
)
from elena.schemas.resume_document import (
    EducationEntry,
    ExperienceEntry,
    ProjectEntry,
    RelevantCoursework,
    ResumeDocument,
    ResumeDocumentPayload,
    ResumeHeading,
    TechnicalSkills,
)
from elena.schemas.user_profile import OverflowSection, UserProfile
from elena.schemas.versioning import (
    RESUME_SCHEMA_V1,
    RESUME_SECTION_ORDER,
    ResumeSchemaVersionV1,
)

__all__ = [
    "RESUME_SCHEMA_V1",
    "RESUME_SECTION_ORDER",
    "ResumeSchemaVersionV1",
    "EducationEntry",
    "ExperienceEntry",
    "OverflowSection",
    "ProjectEntry",
    "RelevantCoursework",
    "ResumeDocument",
    "ResumeDocumentPayload",
    "ResumeHeading",
    "TechnicalSkills",
    "UserProfile",
    "parse_resume_document",
    "parse_resume_document_payload",
    "parse_user_profile",
]
