from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.core.exceptions import (
    AttributeSelectionError,
    AttributeSelectionLineageMismatchError,
    AttributeSelectionRepositoryError,
    AttributeSelectionResultStorageError,
    InvalidAttributeSelectionJobError,
    ProcessingJobRepositoryError,
)
from app.domain.processing_jobs import ProcessingJob, ProcessingJobStatus, ProcessingJobType
from app.services.attribute_selection import AttributeSelectionService
from app.services.attribute_selection_engine import AttributeSelectionEngine
from tests.fixtures.attribute_normalization import NOW, PRODUCT_ID
from tests.unit.test_attribute_selection_engine import pipeline


class Jobs:
    def __init__(self, job):
        self.job, self.updates = job, []

    def get_by_id(self, job_id):
        return self.job if self.job.job_id == job_id else None

    def update(self, job, expected_version):
        self.updates.append(job)
        self.job = replace(
            job, version=expected_version + 1, updated_at=NOW + timedelta(seconds=len(self.updates))
        )
        return self.job


class Results:
    value = None

    def get_by_job_id(self, job_id):
        return self.value

    def create(self, value):
        self.value = value
        return value


def setup_service(*, result_repository=None, jobs_class=Jobs):
    _, normalization, conflict, validation, completeness, _ = pipeline(
        ("voltage", "415", "V"), ("voltage", "440", "V")
    )
    job = ProcessingJob.create(
        product_id=PRODUCT_ID,
        source_id=None,
        job_type=ProcessingJobType.ATTRIBUTE_SELECTION,
        attribute_normalization_id=normalization.normalization_id,
        attribute_conflict_detection_id=conflict.conflict_detection_id,
        attribute_validation_id=validation.validation_id,
        attribute_completeness_id=completeness.completeness_id,
        now=NOW,
    )
    jobs, results = jobs_class(job), result_repository or Results()
    service = AttributeSelectionService(
        job_repository=jobs,
        product_repository=SimpleNamespace(get_by_id=lambda _: object()),
        conflict_repository=SimpleNamespace(get_by_id=lambda _: conflict),
        validation_repository=SimpleNamespace(get_by_id=lambda _: validation),
        completeness_repository=SimpleNamespace(get_by_id=lambda _: completeness),
        normalization_repository=SimpleNamespace(get_by_id=lambda _: normalization),
        result_repository=results,
        engine=AttributeSelectionEngine(),
        clock=lambda: NOW + timedelta(seconds=10),
    )
    return service, jobs, results, (conflict, validation, completeness, normalization)


def test_persists_before_completion_and_sets_reference() -> None:
    service, jobs, results, _ = setup_service()
    result = service.select_for_job(job_id=jobs.job.job_id)
    assert results.value is result
    assert [item.status for item in jobs.updates] == [
        ProcessingJobStatus.RUNNING,
        ProcessingJobStatus.COMPLETED,
    ]
    assert jobs.job.progress_percent == 100 and jobs.job.result_reference.endswith(
        str(result.selection_id)
    )


def test_duplicate_and_lineage_mismatch_do_not_start() -> None:
    existing = Results()
    existing.value = object()
    service, jobs, _, _ = setup_service(result_repository=existing)
    with pytest.raises(InvalidAttributeSelectionJobError):
        service.select_for_job(job_id=jobs.job.job_id)
    service, jobs, _, upstream = setup_service()
    _, validation, _, normalization = upstream
    service._validations = SimpleNamespace(
        get_by_id=lambda _: replace(validation, extraction_id=normalization.normalization_id)
    )
    with pytest.raises(AttributeSelectionLineageMismatchError):
        service.select_for_job(job_id=jobs.job.job_id)
    assert jobs.updates == []


def test_persistence_and_engine_failures_mark_failed() -> None:
    class FailingResults(Results):
        def create(self, value):
            raise AttributeSelectionRepositoryError()

    service, jobs, _, _ = setup_service(result_repository=FailingResults())
    with pytest.raises(AttributeSelectionResultStorageError):
        service.select_for_job(job_id=jobs.job.job_id)
    assert jobs.updates[-1].status is ProcessingJobStatus.FAILED
    service, jobs, _, _ = setup_service()
    service._engine = SimpleNamespace(select=lambda **_: (_ for _ in ()).throw(RuntimeError()))
    with pytest.raises(AttributeSelectionError):
        service.select_for_job(job_id=jobs.job.job_id)
    assert jobs.updates[-1].status is ProcessingJobStatus.FAILED


def test_completion_failure_preserves_result_and_logs_risk(caplog) -> None:
    class CompletionFailingJobs(Jobs):
        def update(self, job, expected_version):
            if self.updates:
                raise ProcessingJobRepositoryError()
            return super().update(job, expected_version)

    service, jobs, results, _ = setup_service(jobs_class=CompletionFailingJobs)
    with pytest.raises(ProcessingJobRepositoryError):
        service.select_for_job(job_id=jobs.job.job_id)
    assert results.value is not None and jobs.job.status is ProcessingJobStatus.RUNNING
    assert "attribute_selection.completion_consistency_risk" in caplog.text
