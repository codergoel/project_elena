"""Schema version identifiers for persisted resume payloads.

See docs/VERSIONING_MODEL.md (ResumeDocument rows use schema_version + JSON payload).
"""

from typing import Final, Literal

# v1 JSON shape matches docs/TEMPLATE_CONTRACT.md §§2–3.
RESUME_SCHEMA_V1: Final[Literal["1"]] = "1"

ResumeSchemaVersionV1 = Literal["1"]

# PDF section order per docs/TEMPLATE_CONTRACT.md §2 (Heading first; then sections).
RESUME_SECTION_ORDER: Final[tuple[str, ...]] = (
    "heading",
    "education",
    "relevant_coursework",
    "experience",
    "projects",
    "technical_skills",
    "leadership_extracurricular",
)
