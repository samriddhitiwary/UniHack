from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.exceptions import (
    AttributeCompletenessConflictResultRequiredError,
    AttributeCompletenessCrossProductLineageError,
    AttributeCompletenessError,
    AttributeCompletenessRepositoryError,
    AttributeCompletenessResultStorageError,
    AttributeCompletenessSchemaMismatchError,
    AttributeCompletenessSchemaNotAvailableError,
    InvalidAttributeCompletenessJobError,
    ProcessingJobRepositoryError,
)
from app.domain.processing_jobs import ProcessingJob, ProcessingJobStatus, ProcessingJobType
from app.services.attribute_completeness import AttributeCompletenessService
from app.services.attribute_completeness_engine import AttributeCompletenessEngine
from tests.fixtures.attribute_normalization import NOW, PRODUCT_ID
from tests.unit.test_attribute_completeness_engine import conflict_for


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


def test_result_persists_before_successful_completion() -> None:
    schema, conflict = conflict_for(("voltage", "415", "V"))
    job = ProcessingJob.create(
        product_id=PRODUCT_ID,
        source_id=None,
        job_type=ProcessingJobType.ATTRIBUTE_COMPLETENESS,
        attribute_conflict_detection_id=conflict.conflict_detection_id,
        now=NOW,
    )
    jobs, results = Jobs(job), Results()
    service = AttributeCompletenessService(
        job_repository=jobs,
        product_repository=SimpleNamespace(get_by_id=lambda _: object()),
        conflict_repository=SimpleNamespace(get_by_id=lambda _: conflict),
        schema_repository=SimpleNamespace(get_by_category_and_version=lambda *_: schema),
        result_repository=results,
        engine=AttributeCompletenessEngine(),
        clock=lambda: NOW + timedelta(seconds=10),
    )
    result = service.evaluate_for_job(job_id=job.job_id)
    assert results.value is result
    assert [item.status for item in jobs.updates] == [
        ProcessingJobStatus.RUNNING,
        ProcessingJobStatus.COMPLETED,
    ]
    assert jobs.job.result_reference.endswith(str(result.completeness_id))


@pytest.mark.parametrize("case", ["product", "conflict", "cross", "missing_schema", "schema"])
def test_prerequisite_failures_do_not_start(case) -> None:
    schema, conflict = conflict_for(("voltage", "415", "V"))
    job = ProcessingJob.create(
        product_id=PRODUCT_ID,
        source_id=None,
        job_type=ProcessingJobType.ATTRIBUTE_COMPLETENESS,
        attribute_conflict_detection_id=conflict.conflict_detection_id,
        now=NOW,
    )
    jobs = Jobs(job)
    conflict_value = (
        None
        if case == "conflict"
        else (
            replace(conflict, product_id=uuid4())
            if case == "cross"
            else replace(conflict, schema_fingerprint="f" * 64)
            if case == "schema"
            else conflict
        )
    )
    service = AttributeCompletenessService(
        job_repository=jobs,
        product_repository=SimpleNamespace(
            get_by_id=lambda _: None if case == "product" else object()
        ),
        conflict_repository=SimpleNamespace(get_by_id=lambda _: conflict_value),
        schema_repository=SimpleNamespace(
            get_by_category_and_version=lambda *_: None if case == "missing_schema" else schema
        ),
        result_repository=Results(),
        engine=AttributeCompletenessEngine(),
        clock=lambda: NOW,
    )
    error = {
        "product": AttributeCompletenessConflictResultRequiredError,
        "conflict": AttributeCompletenessConflictResultRequiredError,
        "cross": AttributeCompletenessCrossProductLineageError,
        "missing_schema": AttributeCompletenessSchemaNotAvailableError,
        "schema": AttributeCompletenessSchemaMismatchError,
    }[case]
    with pytest.raises(error):
        service.evaluate_for_job(job_id=job.job_id)
    assert jobs.updates == []


def _service_with_result_repository(result_repository):
    schema, conflict = conflict_for(("voltage", "415", "V"))
    job = ProcessingJob.create(
        product_id=PRODUCT_ID,
        source_id=None,
        job_type=ProcessingJobType.ATTRIBUTE_COMPLETENESS,
        attribute_conflict_detection_id=conflict.conflict_detection_id,
        now=NOW,
    )
    jobs = Jobs(job)
    return AttributeCompletenessService(
        job_repository=jobs,
        product_repository=SimpleNamespace(get_by_id=lambda _: object()),
        conflict_repository=SimpleNamespace(get_by_id=lambda _: conflict),
        schema_repository=SimpleNamespace(get_by_category_and_version=lambda *_: schema),
        result_repository=result_repository,
        engine=AttributeCompletenessEngine(),
        clock=lambda: NOW + timedelta(seconds=10),
    ), jobs


def test_duplicate_job_is_rejected_before_running() -> None:
    results = Results()
    results.value = object()
    service, jobs = _service_with_result_repository(results)
    with pytest.raises(InvalidAttributeCompletenessJobError):
        service.evaluate_for_job(job_id=jobs.job.job_id)
    assert jobs.updates == []


def test_persistence_failure_marks_running_job_failed() -> None:
    class FailingResults(Results):
        def create(self, value):
            raise AttributeCompletenessRepositoryError()

    service, jobs = _service_with_result_repository(FailingResults())
    with pytest.raises(AttributeCompletenessResultStorageError):
        service.evaluate_for_job(job_id=jobs.job.job_id)
    assert [item.status for item in jobs.updates] == [
        ProcessingJobStatus.RUNNING,
        ProcessingJobStatus.FAILED,
    ]


def test_unexpected_engine_failure_marks_running_job_failed() -> None:
    class FailingEngine(AttributeCompletenessEngine):
        def evaluate(self, **kwargs):
            raise RuntimeError("internal detail")

    service, jobs = _service_with_result_repository(Results())
    service._engine = FailingEngine()
    with pytest.raises(AttributeCompletenessError):
        service.evaluate_for_job(job_id=jobs.job.job_id)
    assert [item.status for item in jobs.updates] == [
        ProcessingJobStatus.RUNNING,
        ProcessingJobStatus.FAILED,
    ]


def test_completion_failure_preserves_result_and_logs_consistency_risk(caplog) -> None:
    class CompletionFailingJobs(Jobs):
        def update(self, job, expected_version):
            if self.updates:
                raise ProcessingJobRepositoryError()
            return super().update(job, expected_version)

    service, original_jobs = _service_with_result_repository(Results())
    jobs = CompletionFailingJobs(original_jobs.job)
    results = Results()
    service._jobs = jobs
    service._results = results
    with pytest.raises(ProcessingJobRepositoryError):
        service.evaluate_for_job(job_id=jobs.job.job_id)
    assert results.value is not None
    assert jobs.job.status is ProcessingJobStatus.RUNNING
    assert "attribute_completeness.completion_consistency_risk" in caplog.text
