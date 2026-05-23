"""User profile / extraction superset (overflow not in v1 Jake template).

See docs/TEMPLATE_CONTRACT.md §6: out-of-contract sections are stored here so they
are not silently dropped. v1 template-only fields live on ResumeDocument.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

_MAX_EXTENSIONS_KEYS = 256
_MAX_EXTENSION_KEY_LEN = 128


class OverflowSection(BaseModel):
    """One unmapped section from PDF import or chat (TEMPLATE_CONTRACT.md §6)."""

    model_config = ConfigDict(extra="forbid")

    unmapped_section_title: str = Field(min_length=1)
    raw_text: str | None = None
    structured: dict[str, JsonValue] = Field(default_factory=dict)


class UserProfile(BaseModel):
    """Structured overflow + bounded extension bag for forward-compatible metadata."""

    model_config = ConfigDict(extra="forbid")

    overflow_sections: list[OverflowSection] = Field(default_factory=list)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("extensions")
    @classmethod
    def _limit_extensions(
        cls,
        v: dict[str, JsonValue],
    ) -> dict[str, JsonValue]:
        if len(v) > _MAX_EXTENSIONS_KEYS:
            msg = f"extensions must have at most {_MAX_EXTENSIONS_KEYS} keys"
            raise ValueError(msg)
        for key in v:
            if len(key) > _MAX_EXTENSION_KEY_LEN:
                msg = f"extension key longer than {_MAX_EXTENSION_KEY_LEN} chars"
                raise ValueError(msg)
        return v
