"""Tests for UserProfile overflow schema (TEMPLATE_CONTRACT §6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from elena.schemas import UserProfile, parse_user_profile
from elena.schemas.user_profile import OverflowSection

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_user_profile_empty_fixture() -> None:
    raw = json.loads((_FIXTURES / "user_profile_empty.json").read_text())
    profile = parse_user_profile(raw)
    assert profile.overflow_sections == []


def test_user_profile_one_overflow_fixture() -> None:
    raw = json.loads((_FIXTURES / "user_profile_one_overflow.json").read_text())
    profile = parse_user_profile(raw)
    assert len(profile.overflow_sections) == 1
    sec = profile.overflow_sections[0]
    assert sec.unmapped_section_title == "Publications"
    assert sec.structured.get("year") == 2024
    assert profile.extensions.get("import_source") == "pdf"


def test_overflow_empty_title_rejected() -> None:
    with pytest.raises(ValidationError):
        OverflowSection.model_validate(
            {"unmapped_section_title": "", "raw_text": "x"},
        )


def test_user_profile_extensions_key_too_long_rejected() -> None:
    long_key = "k" * 129
    with pytest.raises(ValidationError):
        UserProfile.model_validate(
            {"overflow_sections": [], "extensions": {long_key: True}},
        )


def test_user_profile_extensions_too_many_keys_rejected() -> None:
    keys = {f"k{i}": i for i in range(257)}
    with pytest.raises(ValidationError):
        UserProfile.model_validate(
            {"overflow_sections": [], "extensions": keys},
        )


def test_user_profile_extra_top_level_forbidden() -> None:
    with pytest.raises(ValidationError):
        UserProfile.model_validate(
            {
                "overflow_sections": [],
                "extensions": {},
                "unexpected": 1,
            },
        )


def test_round_trip_user_profile() -> None:
    raw = json.loads((_FIXTURES / "user_profile_one_overflow.json").read_text())
    profile = UserProfile.model_validate(raw)
    dumped = profile.model_dump(mode="json")
    again = UserProfile.model_validate(dumped)
    assert again == profile


def test_parse_user_profile_from_string() -> None:
    text = (_FIXTURES / "user_profile_empty.json").read_text()
    profile = parse_user_profile(text)
    assert profile.overflow_sections == []
