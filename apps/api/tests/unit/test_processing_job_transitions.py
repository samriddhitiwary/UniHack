"""Processing-job transition policy tests."""

from dataclasses import replace

import pytest

from app.core.exceptions import InvalidProcessingJobStatusTransitionError
from app.domain.processing_jobs import (
    ProcessingJobStatus,
    is_processing_job_transition_allowed,
    transition_processing_job,
)
from tests.fixtures.processing_jobs import (
    JOB_COMPLETED_AT,
    JOB_STARTED_AT,
    make_processing_job,
)


@pytest.mark.parametrize(
    ("current", "requested"),
    [
        (ProcessingJobStatus.PENDING, ProcessingJobStatus.RUNNING),
        (ProcessingJobStatus.PENDING, ProcessingJobStatus.CANCELLED),
        (ProcessingJobStatus.RUNNING, ProcessingJobStatus.COMPLETED),
        (ProcessingJobStatus.RUNNING, ProcessingJobStatus.FAILED),
        (ProcessingJobStatus.RUNNING, ProcessingJobStatus.CANCELLED),
    ],
)
def test_allowed_transitions(current: ProcessingJobStatus, requested: ProcessingJobStatus) -> None:
    assert is_processing_job_transition_allowed(current, requested)


@pytest.mark.parametrize(
    ("current", "requested"),
    [
        (ProcessingJobStatus.PENDING, ProcessingJobStatus.COMPLETED),
        (ProcessingJobStatus.PENDING, ProcessingJobStatus.FAILED),
        (ProcessingJobStatus.COMPLETED, ProcessingJobStatus.RUNNING),
        (ProcessingJobStatus.FAILED, ProcessingJobStatus.RUNNING),
        (ProcessingJobStatus.CANCELLED, ProcessingJobStatus.RUNNING),
        (ProcessingJobStatus.COMPLETED, ProcessingJobStatus.FAILED),
    ],
)
def test_rejected_transitions(current: ProcessingJobStatus, requested: ProcessingJobStatus) -> None:
    assert not is_processing_job_transition_allowed(current, requested)


def test_running_and_terminal_transitions_apply_timestamps_and_completion_rules() -> None:
    running = transition_processing_job(
        make_processing_job(), ProcessingJobStatus.RUNNING, now=JOB_STARTED_AT
    )
    assert running.started_at == JOB_STARTED_AT and running.completed_at is None
    dirty = replace(running, progress_percent=50, error_code="OLD", error_message="Old")
    completed = transition_processing_job(
        dirty, ProcessingJobStatus.COMPLETED, now=JOB_COMPLETED_AT
    )
    assert completed.completed_at == JOB_COMPLETED_AT and completed.progress_percent == 100
    assert completed.error_code is None and completed.error_message is None


@pytest.mark.parametrize("terminal", [ProcessingJobStatus.FAILED, ProcessingJobStatus.CANCELLED])
def test_failed_and_cancelled_set_completed_at(terminal: ProcessingJobStatus) -> None:
    running = transition_processing_job(
        make_processing_job(), ProcessingJobStatus.RUNNING, now=JOB_STARTED_AT
    )
    transitioned = transition_processing_job(running, terminal, now=JOB_COMPLETED_AT)
    assert transitioned.completed_at == JOB_COMPLETED_AT


def test_terminal_state_cannot_transition() -> None:
    running = transition_processing_job(
        make_processing_job(), ProcessingJobStatus.RUNNING, now=JOB_STARTED_AT
    )
    completed = transition_processing_job(
        running, ProcessingJobStatus.COMPLETED, now=JOB_COMPLETED_AT
    )
    with pytest.raises(InvalidProcessingJobStatusTransitionError):
        transition_processing_job(completed, ProcessingJobStatus.RUNNING)
