from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.exceptions import (
    AttributeValidationCrossProductLineageError,
    AttributeValidationError,
    AttributeValidationNormalizationRequiredError,
    AttributeValidationRepositoryError,
    AttributeValidationResultStorageError,
    AttributeValidationSchemaMismatchError,
    AttributeValidationSchemaNotAvailableError,
    InvalidAttributeValidationJobError,
    ProcessingJobRepositoryError,
)
from app.domain.processing_jobs import ProcessingJob, ProcessingJobStatus, ProcessingJobType
from app.services.attribute_validation import AttributeValidationService
from app.services.attribute_validation_engine import AttributeValidationEngine
from tests.fixtures.attribute_normalization import NOW, PRODUCT_ID
from tests.unit.test_attribute_validation_engine import normalized


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
    schema, normalization = normalized(("voltage", "415", "V"))
    job = ProcessingJob.create(
        product_id=PRODUCT_ID,
        source_id=None,
        job_type=ProcessingJobType.ATTRIBUTE_VALIDATION,
        attribute_normalization_id=normalization.normalization_id,
        now=NOW,
    )
    jobs = jobs_class(job)
    results = result_repository or Results()
    service = AttributeValidationService(
        job_repository=jobs,
        product_repository=SimpleNamespace(get_by_id=lambda _: object()),
        normalization_repository=SimpleNamespace(get_by_id=lambda _: normalization),
        schema_repository=SimpleNamespace(get_by_category_and_version=lambda *_: schema),
        result_repository=results,
        engine=AttributeValidationEngine(),
        clock=lambda: NOW + timedelta(seconds=10),
    )
    return service, jobs, results, schema, normalization


def test_result_persists_before_completion_and_reference_is_set() -> None:
    service, jobs, results, _, normalization = setup_service()
    result = service.validate_for_job(job_id=jobs.job.job_id)
    assert results.value is result and result.normalization_id == normalization.normalization_id
    assert [item.status for item in jobs.updates] == [
        ProcessingJobStatus.RUNNING,
        ProcessingJobStatus.COMPLETED,
    ]
    assert jobs.job.result_reference.endswith(str(result.validation_id))


@pytest.mark.parametrize("case", ["product", "normalization", "cross", "missing_schema", "schema"])
def test_prerequisite_failures_do_not_start(case) -> None:
    service, jobs, _, schema, normalization = setup_service()
    service._products = SimpleNamespace(get_by_id=lambda _: None if case == "product" else object())
    service._normalizations = SimpleNamespace(
        get_by_id=lambda _: (
            None
            if case == "normalization"
            else replace(normalization, product_id=uuid4())
            if case == "cross"
            else replace(normalization, schema_fingerprint="f" * 64)
            if case == "schema"
            else normalization
        )
    )
    service._schemas = SimpleNamespace(
        get_by_category_and_version=lambda *_: None if case == "missing_schema" else schema
    )
    error = {
        "product": AttributeValidationNormalizationRequiredError,
        "normalization": AttributeValidationNormalizationRequiredError,
        "cross": AttributeValidationCrossProductLineageError,
        "missing_schema": AttributeValidationSchemaNotAvailableError,
        "schema": AttributeValidationSchemaMismatchError,
    }[case]
    with pytest.raises(error):
        service.validate_for_job(job_id=jobs.job.job_id)
    assert jobs.updates == []


def test_duplicate_invalid_job_and_persistence_failure() -> None:
    results = Results()
    results.value = object()
    service, jobs, _, _, _ = setup_service(result_repository=results)
    with pytest.raises(InvalidAttributeValidationJobError):
        service.validate_for_job(job_id=jobs.job.job_id)

    class FailingResults(Results):
        def create(self, value):
            raise AttributeValidationRepositoryError()

    service, jobs, _, _, _ = setup_service(result_repository=FailingResults())
    with pytest.raises(AttributeValidationResultStorageError):
        service.validate_for_job(job_id=jobs.job.job_id)
    assert jobs.updates[-1].status is ProcessingJobStatus.FAILED


def test_engine_failure_marks_failed_and_completion_failure_preserves_result(caplog) -> None:
    service, jobs, _, _, _ = setup_service()
    service._engine = SimpleNamespace(validate=lambda **_: (_ for _ in ()).throw(RuntimeError()))
    with pytest.raises(AttributeValidationError):
        service.validate_for_job(job_id=jobs.job.job_id)
    assert jobs.updates[-1].status is ProcessingJobStatus.FAILED

    class CompletionFailingJobs(Jobs):
        def update(self, job, expected_version):
            if self.updates:
                raise ProcessingJobRepositoryError()
            return super().update(job, expected_version)

    service, jobs, results, _, _ = setup_service(jobs_class=CompletionFailingJobs)
    with pytest.raises(ProcessingJobRepositoryError):
        service.validate_for_job(job_id=jobs.job.job_id)
    assert results.value is not None and jobs.job.status is ProcessingJobStatus.RUNNING
    assert "attribute_validation.completion_consistency_risk" in caplog.text
