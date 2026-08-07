"""Processing-job domain model."""

from app.domain.processing_jobs.compatibility import is_processing_job_type_supported
from app.domain.processing_jobs.entities import ProcessingJob, ProcessingJobPage
from app.domain.processing_jobs.enums import ProcessingJobStatus, ProcessingJobType
from app.domain.processing_jobs.transitions import (
    is_processing_job_transition_allowed,
    transition_processing_job,
)

__all__ = [
    "ProcessingJob",
    "ProcessingJobPage",
    "ProcessingJobStatus",
    "ProcessingJobType",
    "is_processing_job_transition_allowed",
    "is_processing_job_type_supported",
    "transition_processing_job",
]
