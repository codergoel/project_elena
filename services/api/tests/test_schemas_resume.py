"""Tests for ResumeDocument and ResumeDocumentPayload (TEMPLATE_CONTRACT §3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from elena.schemas import (
    RESUME_SCHEMA_V1,
    parse_resume_document,
    parse_resume_document_payload,
)
from elena.schemas.resume_document import ResumeDocument, ResumeDocumentPayload

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_resume_minimal_fixture_loads() -> None:
    raw = json.loads((_FIXTURES / "resume_minimal.json").read_text())
    doc = parse_resume_document(raw)
    assert doc.heading.full_name == "Jane Doe"
    assert doc.education == []
    assert doc.experience == []


def test_resume_full_fixture_loads() -> None:
    raw = json.loads((_FIXTURES / "resume_full.json").read_text())
    doc = parse_resume_document(raw)
    assert doc.heading.email is not None
    assert len(doc.education) == 1
    assert doc.relevant_coursework is not None
    assert len(doc.relevant_coursework.courses) == 4
    assert len(doc.experience) == 1
    assert len(doc.experience[0].bullets) == 2
    assert len(doc.projects) == 1
    assert doc.technical_skills is not None
    assert doc.technical_skills.languages is not None
    assert len(doc.leadership_extracurricular) == 1


def test_missing_full_name_rejected() -> None:
    with pytest.raises(ValidationError):
        ResumeDocument.model_validate({"heading": {}})


def test_extra_top_level_key_forbidden() -> None:
    with pytest.raises(ValidationError):
        ResumeDocument.model_validate(
            {
                "heading": {"full_name": "A"},
                "summary": "Nope",
            },
        )


def test_invalid_github_url_rejected() -> None:
    with pytest.raises(ValidationError):
        ResumeDocument.model_validate(
            {
                "heading": {
                    "full_name": "A",
                    "github_url": "not-a-valid-url",
                },
            },
        )


def test_empty_bullets_allowed() -> None:
    doc = ResumeDocument.model_validate(
        {
            "heading": {"full_name": "A"},
            "experience": [
                {
                    "organization": "Co",
                    "date_range": "2020 -- 2021",
                    "title": "Eng",
                    "location": "NYC",
                    "bullets": [],
                },
            ],
        },
    )
    assert doc.experience[0].bullets == []


def test_round_trip_json_stable() -> None:
    raw = json.loads((_FIXTURES / "resume_full.json").read_text())
    doc = ResumeDocument.model_validate(raw)
    dumped = doc.model_dump(mode="json")
    again = ResumeDocument.model_validate(dumped)
    assert again == doc


def test_payload_default_schema_version() -> None:
    raw = json.loads((_FIXTURES / "resume_minimal.json").read_text())
    payload = ResumeDocumentPayload.model_validate({"document": raw})
    assert payload.schema_version == RESUME_SCHEMA_V1


def test_payload_explicit_schema_version() -> None:
    raw = json.loads((_FIXTURES / "resume_minimal.json").read_text())
    wrapped = {"schema_version": RESUME_SCHEMA_V1, "document": raw}
    payload = parse_resume_document_payload(wrapped)
    assert payload.document.heading.full_name == "Jane Doe"


def test_payload_wrong_schema_version_rejected() -> None:
    raw = json.loads((_FIXTURES / "resume_minimal.json").read_text())
    with pytest.raises(ValidationError):
        ResumeDocumentPayload.model_validate(
            {"schema_version": "999", "document": raw},
        )


def test_parse_resume_document_from_string() -> None:
    text = (_FIXTURES / "resume_minimal.json").read_text()
    doc = parse_resume_document(text)
    assert doc.heading.full_name == "Jane Doe"
