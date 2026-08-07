"""Central processing-job transition and timestamp policy."""

from dataclasses import replace
from datetime import UTC, datetime

from app.core.exceptions import InvalidProcessingJobStatusTransitionError
from app.domain.processing_jobs.entities import ProcessingJob
from app.domain.processing_jobs.enums import ProcessingJobStatus

_ALLOWED: dict[ProcessingJobStatus, frozenset[ProcessingJobStatus]] = {
    ProcessingJobStatus.PENDING: frozenset(
        {ProcessingJobStatus.RUNNING, ProcessingJobStatus.CANCELLED}
    ),
    ProcessingJobStatus.RUNNING: frozenset(
        {
            ProcessingJobStatus.COMPLETED,
            ProcessingJobStatus.FAILED,
            ProcessingJobStatus.CANCELLED,
        }
    ),
    ProcessingJobStatus.COMPLETED: frozenset(),
    ProcessingJobStatus.FAILED: frozenset(),
    ProcessingJobStatus.CANCELLED: frozenset(),
}


def is_processing_job_transition_allowed(
    current: ProcessingJobStatus, requested: ProcessingJobStatus
) -> bool:
    return requested in _ALLOWED[current]


def transition_processing_job(
    job: ProcessingJob,
    requested: ProcessingJobStatus,
    *,
    now: datetime | None = None,
) -> ProcessingJob:
    if not is_processing_job_transition_allowed(job.status, requested):
        raise InvalidProcessingJobStatusTransitionError(
            job.job_id, job.status.value, requested.value
        )
    timestamp = (now or datetime.now(UTC)).astimezone(UTC)
    if requested is ProcessingJobStatus.RUNNING:
        return replace(job, status=requested, started_at=timestamp)
    if requested is ProcessingJobStatus.COMPLETED:
        return replace(
            job,
            status=requested,
            completed_at=timestamp,
            progress_percent=100,
            error_code=None,
            error_message=None,
        )
    return replace(job, status=requested, completed_at=timestamp)
