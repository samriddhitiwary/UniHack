"""Immutable processing-job entities and invariants."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from app.domain.processing_jobs.enums import ProcessingJobStatus, ProcessingJobType

ERROR_CODE_MAX_LENGTH = 100
ERROR_MESSAGE_MAX_LENGTH = 2_000
RESULT_REFERENCE_MAX_LENGTH = 1_024
_WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")


def _utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(UTC)


def _optional_text(value: str | None, field: str, maximum: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > maximum:
        raise ValueError(f"{field} must contain at most {maximum} characters")
    return normalized


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessingJob:
    job_id: UUID
    product_id: UUID
    source_id: UUID | None
    classification_id: UUID | None = None
    job_type: ProcessingJobType
    status: ProcessingJobStatus
    attempt: int
    progress_percent: int
    error_code: str | None
    error_message: str | None
    result_reference: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime
    version: int

    def __post_init__(self) -> None:
        if not isinstance(self.job_id, UUID):
            raise ValueError("job_id must be a UUID")
        if not isinstance(self.product_id, UUID):
            raise ValueError("product_id must be a UUID")
        if not isinstance(self.job_type, ProcessingJobType):
            raise ValueError("job_type must be a ProcessingJobType")
        if self.job_type in {
            ProcessingJobType.PRODUCT_CLASSIFICATION,
            ProcessingJobType.ATTRIBUTE_EXTRACTION,
        }:
            if self.source_id is not None:
                raise ValueError("product-level jobs must not have a source_id")
        elif not isinstance(self.source_id, UUID):
            raise ValueError("source_id must be a UUID for source-scoped jobs")
        if self.job_type is ProcessingJobType.ATTRIBUTE_EXTRACTION:
            if not isinstance(self.classification_id, UUID):
                raise ValueError("ATTRIBUTE_EXTRACTION jobs require a classification_id")
        elif self.classification_id is not None:
            raise ValueError("classification_id is only valid for ATTRIBUTE_EXTRACTION jobs")
        if not isinstance(self.status, ProcessingJobStatus):
            raise ValueError("status must be a ProcessingJobStatus")
        if isinstance(self.attempt, bool) or not isinstance(self.attempt, int) or self.attempt < 1:
            raise ValueError("attempt must be a positive integer")
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise ValueError("version must be a positive integer")
        if (
            isinstance(self.progress_percent, bool)
            or not isinstance(self.progress_percent, int)
            or not 0 <= self.progress_percent <= 100
        ):
            raise ValueError("progress_percent must be between 0 and 100")

        created = _utc(self.created_at, "created_at")
        updated = _utc(self.updated_at, "updated_at")
        started = _utc(self.started_at, "started_at") if self.started_at else None
        completed = _utc(self.completed_at, "completed_at") if self.completed_at else None
        if updated < created:
            raise ValueError("updated_at cannot precede created_at")
        if started is not None and started < created:
            raise ValueError("started_at cannot precede created_at")
        if completed is not None and completed < (started or created):
            raise ValueError("completed_at cannot precede job activity")

        error_code = _optional_text(self.error_code, "error_code", ERROR_CODE_MAX_LENGTH)
        error_message = _optional_text(
            self.error_message, "error_message", ERROR_MESSAGE_MAX_LENGTH
        )
        result_reference = _optional_text(
            self.result_reference, "result_reference", RESULT_REFERENCE_MAX_LENGTH
        )
        if result_reference is not None and (
            result_reference.startswith(("/", "\\"))
            or _WINDOWS_PATH.match(result_reference)
            or "\\" in result_reference
            or ".." in result_reference.split("/")
        ):
            raise ValueError("result_reference must be a safe logical reference")

        if self.status is ProcessingJobStatus.PENDING and (
            started is not None or completed is not None or self.progress_percent != 0
        ):
            raise ValueError("PENDING jobs must be unstarted at zero progress")
        if self.status is ProcessingJobStatus.RUNNING and (
            started is None or completed is not None or self.progress_percent >= 100
        ):
            raise ValueError("RUNNING jobs require a start and progress below 100")
        if self.status is ProcessingJobStatus.COMPLETED and (
            started is None
            or completed is None
            or self.progress_percent != 100
            or error_code is not None
            or error_message is not None
        ):
            raise ValueError("COMPLETED jobs require timestamps, 100 progress, and no error")
        if self.status in {ProcessingJobStatus.FAILED, ProcessingJobStatus.CANCELLED} and (
            completed is None
        ):
            raise ValueError("terminal jobs require completed_at")

        object.__setattr__(self, "error_code", error_code)
        object.__setattr__(self, "error_message", error_message)
        object.__setattr__(self, "result_reference", result_reference)
        object.__setattr__(self, "created_at", created)
        object.__setattr__(self, "started_at", started)
        object.__setattr__(self, "completed_at", completed)
        object.__setattr__(self, "updated_at", updated)

    @classmethod
    def create(
        cls,
        *,
        product_id: UUID,
        source_id: UUID | None,
        job_type: ProcessingJobType,
        classification_id: UUID | None = None,
        attempt: int = 1,
        now: datetime | None = None,
    ) -> Self:
        timestamp = _utc(now or datetime.now(UTC), "now")
        return cls(
            job_id=uuid4(),
            product_id=product_id,
            source_id=source_id,
            classification_id=classification_id,
            job_type=job_type,
            status=ProcessingJobStatus.PENDING,
            attempt=attempt,
            progress_percent=0,
            error_code=None,
            error_message=None,
            result_reference=None,
            created_at=timestamp,
            started_at=None,
            completed_at=None,
            updated_at=timestamp,
            version=1,
        )


@dataclass(frozen=True, slots=True)
class ProcessingJobPage:
    items: tuple[ProcessingJob, ...]
    next_cursor: str | None
