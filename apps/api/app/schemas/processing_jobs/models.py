"""Pydantic schemas for processing-job boundaries."""

import re
from typing import ClassVar, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.json_schema import SkipJsonSchema

from app.domain.processing_jobs import ProcessingJob, ProcessingJobStatus, ProcessingJobType
from app.domain.processing_jobs.entities import (
    ERROR_CODE_MAX_LENGTH,
    ERROR_MESSAGE_MAX_LENGTH,
    RESULT_REFERENCE_MAX_LENGTH,
)
from app.schemas.products.models import to_camel

_WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")


class ProcessingJobSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
        str_strip_whitespace=True,
    )

    @field_validator(
        "error_code", "error_message", "result_reference", mode="before", check_fields=False
    )
    @classmethod
    def blank_optional_text_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("result_reference", check_fields=False)
    @classmethod
    def safe_result_reference(cls, value: str | None) -> str | None:
        if value is not None and (
            value.startswith(("/", "\\"))
            or _WINDOWS_PATH.match(value)
            or "\\" in value
            or ".." in value.split("/")
        ):
            raise ValueError("result_reference must be a safe logical reference")
        return value


class ProcessingJobCreate(ProcessingJobSchema):
    product_id: UUID
    source_id: UUID | None
    job_type: ProcessingJobType
    attempt: int = Field(default=1, ge=1, strict=True)

    @model_validator(mode="after")
    def validate_create(self) -> Self:
        ProcessingJob.create(**self.model_dump(by_alias=False))
        return self


class ProcessingJobCreateRequest(ProcessingJobSchema):
    """Strict API body; product/source identity comes only from the route path."""

    model_config = ConfigDict(
        populate_by_name=False,
        validate_by_alias=True,
        validate_by_name=False,
    )

    job_type: ProcessingJobType


class ProcessingJobUpdate(ProcessingJobSchema):
    editable_fields: ClassVar[frozenset[str]] = frozenset(
        {"status", "progress_percent", "error_code", "error_message", "result_reference"}
    )

    version: int = Field(ge=1, strict=True)
    status: ProcessingJobStatus | SkipJsonSchema[None] = None
    progress_percent: int | None = Field(default=None, ge=0, le=100, strict=True)
    error_code: str | None = Field(default=None, max_length=ERROR_CODE_MAX_LENGTH)
    error_message: str | None = Field(default=None, max_length=ERROR_MESSAGE_MAX_LENGTH)
    result_reference: str | None = Field(default=None, max_length=RESULT_REFERENCE_MAX_LENGTH)

    @model_validator(mode="after")
    def validate_update(self) -> Self:
        supplied = self.model_fields_set & self.editable_fields
        if not supplied:
            raise ValueError("at least one editable processing-job field is required")
        if "status" in supplied and self.status is None:
            raise ValueError("status cannot be null")
        if "progress_percent" in supplied and self.progress_percent is None:
            raise ValueError("progress_percent cannot be null")
        return self


class ProcessingJobRecord(ProcessingJobSchema):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    job_id: UUID
    product_id: UUID
    source_id: UUID | None
    job_type: ProcessingJobType
    status: ProcessingJobStatus
    attempt: int = Field(ge=1)
    progress_percent: int = Field(ge=0, le=100)
    error_code: str | None = Field(max_length=ERROR_CODE_MAX_LENGTH)
    error_message: str | None = Field(max_length=ERROR_MESSAGE_MAX_LENGTH)
    result_reference: str | None = Field(max_length=RESULT_REFERENCE_MAX_LENGTH)
    created_at: AwareDatetime
    started_at: AwareDatetime | None
    completed_at: AwareDatetime | None
    updated_at: AwareDatetime
    version: int = Field(ge=1)


class ProcessingJobListResult(ProcessingJobSchema):
    items: list[ProcessingJobRecord]
    next_cursor: str | None = None
