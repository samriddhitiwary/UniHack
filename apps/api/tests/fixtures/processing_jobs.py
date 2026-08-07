"""Deterministic processing-job fixtures."""

from datetime import UTC, datetime
from uuid import UUID

from app.domain.processing_jobs import ProcessingJob, ProcessingJobStatus, ProcessingJobType
from tests.fixtures.product_sources import SOURCE_ID
from tests.fixtures.products import PRODUCT_ID

JOB_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
SECOND_JOB_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
JOB_CREATED_AT = datetime(2026, 8, 7, 6, 0, tzinfo=UTC)
JOB_STARTED_AT = datetime(2026, 8, 7, 6, 5, tzinfo=UTC)
JOB_COMPLETED_AT = datetime(2026, 8, 7, 6, 10, tzinfo=UTC)
JOB_UPDATED_AT = datetime(2026, 8, 7, 6, 15, tzinfo=UTC)


def make_processing_job(
    *,
    job_id: UUID = JOB_ID,
    product_id: UUID = PRODUCT_ID,
    source_id: UUID = SOURCE_ID,
    job_type: ProcessingJobType = ProcessingJobType.SOURCE_PROCESSING,
    status: ProcessingJobStatus = ProcessingJobStatus.PENDING,
    attempt: int = 1,
    progress_percent: int = 0,
    error_code: str | None = None,
    error_message: str | None = None,
    result_reference: str | None = None,
    created_at: datetime = JOB_CREATED_AT,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    updated_at: datetime = JOB_CREATED_AT,
    version: int = 1,
) -> ProcessingJob:
    return ProcessingJob(
        job_id=job_id,
        product_id=product_id,
        source_id=source_id,
        job_type=job_type,
        status=status,
        attempt=attempt,
        progress_percent=progress_percent,
        error_code=error_code,
        error_message=error_message,
        result_reference=result_reference,
        created_at=created_at,
        started_at=started_at,
        completed_at=completed_at,
        updated_at=updated_at,
        version=version,
    )
