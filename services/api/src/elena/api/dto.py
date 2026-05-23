"""HTTP-facing DTOs."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, model_validator

from elena.db.models import BaseResumeSource
from elena.schemas.resume_document import EducationEntry, ExperienceEntry, ResumeDocumentPayload
from elena.schemas.user_profile import UserProfile


class BaseResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    source: BaseResumeSource
    active_document_id: uuid.UUID | None
    import_source_pdf_key: str | None = None


class BaseCreateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    source: BaseResumeSource = BaseResumeSource.GUIDED


class VariantForkBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = None
    jd_plaintext: str | None = Field(
        None,
        description="Optional job description text stored as a private blob (Phase 8.1).",
    )


class VariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    base_resume_id: uuid.UUID
    label: str
    jd_blob_key: str | None
    forked_from_document_id: uuid.UUID | None
    active_document_id: uuid.UUID | None


class VariantForkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant: VariantRead
    jd_download_url: str | None = None


class ConflictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str
    variants_remaining: int


class RenderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pdf_url: str
    compile_ok: bool
    page_count: int | None
    log_tail: str
    latex_user_hint: str | None = Field(
        default=None,
        description="Concise LaTeX error line when compile_ok is false (Phase 9.2)",
    )


class BaseResumeExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exported_at: datetime
    resume: BaseResumeRead
    envelope: ResumeDocumentPayload


class VariantResumeExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exported_at: datetime
    variant: VariantRead
    envelope: ResumeDocumentPayload


class ImportMapBody(BaseModel):
    """Exactly one field should be set: pasted text after upload or a blob key."""

    model_config = ConfigDict(extra="forbid")

    extracted_text: str | None = None
    pdf_key: str | None = Field(None, pattern=r"[0-9a-f]{32}\.pdf")


class ImportCommitBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    envelope: ResumeDocumentPayload
    user_profile: UserProfile
    pdf_key: str | None = Field(None, pattern=r"[0-9a-f]{32}\.pdf")


class ImportPdfUploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pdf_key: str
    page_count: int
    truncated: bool
    extracted_chars: int
    extracted_text: str


class ImportPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume: ResumeDocumentPayload
    user_profile: UserProfile
    field_confidence: dict[str, float]
    overall_confidence: float


class ImportCommitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_resume: BaseResumeRead
    source_pdf_download_url: str | None


# --- Phase 6 guided intake (FSM / no LLM) ---


class GuidedCheckpointRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skipped_slots: list[str]


class GuidedStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bootstrap_required: bool
    terminal: bool
    next_slot: str | None
    prompt: str | None
    checkpoint: GuidedCheckpointRead
    resume: ResumeDocumentPayload | None


class GuidedBootstrapResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_resume: BaseResumeRead


class GuidedHeadingCommitBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1)
    email: EmailStr | None = None
    phone: str | None = None
    address_line: str | None = None
    linkedin_url: HttpUrl | None = None
    github_url: HttpUrl | None = None


class GuidedEducationCommitBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skip: bool = False
    entry: EducationEntry | None = None

    @model_validator(mode="after")
    def _skip_xor_entry(self) -> GuidedEducationCommitBody:
        if self.skip:
            if self.entry is not None:
                raise ValueError("omit entry when skip=true")
            return self
        if self.entry is None:
            raise ValueError("entry is required when skip=false")
        return self


class GuidedExperienceCommitBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skip: bool = False
    entry: ExperienceEntry | None = None

    @model_validator(mode="after")
    def _skip_xor_entry(self) -> GuidedExperienceCommitBody:
        if self.skip:
            if self.entry is not None:
                raise ValueError("omit entry when skip=true")
            return self
        if self.entry is None:
            raise ValueError("entry is required when skip=false")
        return self


class GuidedSkillsCommitBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skip: bool = False
    languages: str | None = None

    @model_validator(mode="after")
    def _skip_xor_langs(self) -> GuidedSkillsCommitBody:
        if self.skip:
            if self.languages is not None:
                raise ValueError("omit languages when skip=true")
            return self
        if not self.languages or not str(self.languages).strip():
            raise ValueError("languages is required when skip=false")
        return self


class ConversationThreadRead(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    langgraph_thread_id: str
    base_resume_id: uuid.UUID | None
    variant_id: uuid.UUID | None


class AgentTurnBody(BaseModel):
    """One synchronous LLM agent turn using tools + LangGraph Postgres checkpoints."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, description="User message")


class AgentTurnResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assistant: str
    thread_id: uuid.UUID
    last_pdf_url: str | None = None
