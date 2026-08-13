from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.exceptions import (
    StructuredAttributeExtractionLimitExceededError,
    StructuredAttributeExtractionPrerequisiteError,
)
from app.domain.category_schemas.builtins import induction_motor_schema_v1
from app.domain.processing_jobs import ProcessingJob, ProcessingJobStatus, ProcessingJobType
from app.domain.product_classification import ProductClassificationStatus
from app.domain.products import ProductCategory
from app.services.structured_attribute_extraction import StructuredAttributeExtractionService
from app.services.structured_attribute_extraction_engine import StructuredAttributeExtractionEngine

NOW = datetime(2026, 8, 13, tzinfo=UTC)


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
    def __init__(self):
        self.value = None

    def get_by_job_id(self, job_id):
        return self.value

    def create(self, value):
        self.value = value
        return value


def make_service(*, product_exists=True, classified=True, evidence_error=None):
    classification_id, product_id = uuid4(), uuid4()
    job = ProcessingJob.create(
        product_id=product_id,
        source_id=None,
        job_type=ProcessingJobType.ATTRIBUTE_EXTRACTION,
        classification_id=classification_id,
        now=NOW,
    )
    classification = SimpleNamespace(
        classification_id=classification_id,
        product_id=product_id,
        category=ProductCategory.INDUCTION_MOTOR,
        status=ProductClassificationStatus.CLASSIFIED
        if classified
        else ProductClassificationStatus.AMBIGUOUS,
    )
    jobs, results = Jobs(job), Results()
    service = StructuredAttributeExtractionService(
        job_repository=jobs,
        product_repository=SimpleNamespace(
            get_by_id=lambda _: object() if product_exists else None
        ),
        classification_repository=SimpleNamespace(get_by_id=lambda _: classification),
        schema_repository=SimpleNamespace(
            get_active_by_category=lambda _: induction_motor_schema_v1()
        ),
        result_repository=results,
        evidence_aggregator=SimpleNamespace(
            collect=lambda _: (_ for _ in ()).throw(evidence_error) if evidence_error else ((), ())
        ),
        engine=StructuredAttributeExtractionEngine(),
        clock=lambda: NOW + timedelta(seconds=10),
    )
    return service, jobs, results


def test_no_candidate_run_persists_before_completing() -> None:
    service, jobs, results = make_service()
    value = service.extract_for_job(job_id=jobs.job.job_id)
    assert results.value is value
    assert [item.status for item in jobs.updates] == [
        ProcessingJobStatus.RUNNING,
        ProcessingJobStatus.COMPLETED,
    ]
    assert jobs.job.result_reference.endswith(str(value.extraction_id))


@pytest.mark.parametrize("product_exists,classified", [(False, True), (True, False)])
def test_prerequisites_are_rejected_before_running(product_exists, classified) -> None:
    service, jobs, _ = make_service(product_exists=product_exists, classified=classified)
    with pytest.raises(StructuredAttributeExtractionPrerequisiteError):
        service.extract_for_job(job_id=jobs.job.job_id)
    assert jobs.updates == []


def test_post_start_limit_failure_marks_job_failed_with_safe_error() -> None:
    service, jobs, _ = make_service(
        evidence_error=StructuredAttributeExtractionLimitExceededError()
    )
    with pytest.raises(StructuredAttributeExtractionLimitExceededError):
        service.extract_for_job(job_id=jobs.job.job_id)
    assert [item.status for item in jobs.updates] == [
        ProcessingJobStatus.RUNNING,
        ProcessingJobStatus.FAILED,
    ]
    assert jobs.job.error_code == "ATTRIBUTE_EXTRACTION_LIMIT_EXCEEDED"
