"""Parse and validate untrusted dict/JSON into schema models."""

from __future__ import annotations

from typing import Any

from elena.schemas.resume_document import ResumeDocument, ResumeDocumentPayload
from elena.schemas.user_profile import UserProfile


def parse_resume_document(data: dict[str, Any] | str) -> ResumeDocument:
    """Validate raw JSON as a ResumeDocument; raises ValidationError on failure."""
    if isinstance(data, str):
        return ResumeDocument.model_validate_json(data)
    return ResumeDocument.model_validate(data)


def parse_resume_document_payload(data: dict[str, Any] | str) -> ResumeDocumentPayload:
    """Validate envelope with schema_version + document."""
    if isinstance(data, str):
        return ResumeDocumentPayload.model_validate_json(data)
    return ResumeDocumentPayload.model_validate(data)


def parse_user_profile(data: dict[str, Any] | str) -> UserProfile:
    """Validate raw JSON as a UserProfile."""
    if isinstance(data, str):
        return UserProfile.model_validate_json(data)
    return UserProfile.model_validate(data)
