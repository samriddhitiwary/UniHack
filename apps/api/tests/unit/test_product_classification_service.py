"""Product-classification orchestration and lifecycle tests."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.exceptions import (
    InvalidProductClassificationJobError,
    ProductClassificationEvidenceLimitExceededError,
)
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
)
from app.domain.product_classification import ClassificationEvidence, ClassificationEvidenceType
from app.domain.products import ProductCategory
from app.services.product_classification import ProductClassificationService
from app.services.product_classification_engine import ProductClassificationEngine

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class Jobs:
    def __init__(self, job):
        self.job = job
        self.updates = []

    def get_by_id(self, job_id):
        return self.job if self.job.job_id == job_id else None

    def update(self, job, expected_version):
        self.updates.append(job)
        self.job = replace(
            job, version=expected_version + 1, updated_at=NOW + timedelta(seconds=len(self.updates))
        )
        return self.job


class Products:
    def __init__(self, product):
        self.product = product

    def get_by_id(self, product_id):
        return self.product if self.product and self.product.product_id == product_id else None


class Results:
    def __init__(self):
        self.result = None

    def get_by_job_id(self, job_id):
        return self.result

    def create(self, result):
        self.result = result
        return result


class Evidence:
    def __init__(self, values=(), error=None):
        self.values, self.error = values, error

    def collect(self, product_id):
        if self.error:
            raise self.error
        return self.values


def make_job() -> ProcessingJob:
    return ProcessingJob.create(
        product_id=uuid4(),
        source_id=None,
        job_type=ProcessingJobType.PRODUCT_CLASSIFICATION,
        now=NOW,
    )


def service(job, evidence=(), error=None):
    jobs = Jobs(job)
    product = SimpleNamespace(product_id=job.product_id, category=ProductCategory.UNCLASSIFIED)
    results = Results()
    instance = ProductClassificationService(
        job_repository=jobs,
        product_repository=Products(product),
        result_repository=results,
        evidence_aggregator=Evidence(evidence, error),
        engine=ProductClassificationEngine(),
        clock=lambda: NOW + timedelta(seconds=10),
    )
    return instance, jobs, product, results


def test_classified_result_completes_job_without_mutating_product() -> None:
    job = make_job()
    item = ClassificationEvidence(
        evidence_id="evidence-000001",
        source_id=uuid4(),
        evidence_type=ClassificationEvidenceType.DIRECT_TEXT,
        text="centrifugal pump",
        location="source",
        weight=100,
    )
    instance, jobs, product, results = service(job, (item,))
    result = instance.classify_for_job(job_id=job.job_id)
    assert result.category is ProductCategory.CENTRIFUGAL_PUMP
    assert results.result is result
    assert [update.status for update in jobs.updates] == [
        ProcessingJobStatus.RUNNING,
        ProcessingJobStatus.COMPLETED,
    ]
    assert jobs.job.result_reference == f"product-classification-results/{result.classification_id}"
    assert product.category is ProductCategory.UNCLASSIFIED


def test_insufficient_evidence_is_successfully_completed() -> None:
    job = make_job()
    instance, jobs, _, _ = service(job)
    result = instance.classify_for_job(job_id=job.job_id)
    assert result.category is ProductCategory.UNCLASSIFIED
    assert jobs.job.status is ProcessingJobStatus.COMPLETED


def test_wrong_job_type_is_rejected_before_start() -> None:
    job = ProcessingJob.create(
        product_id=uuid4(),
        source_id=uuid4(),
        job_type=ProcessingJobType.CSV_PROCESSING,
        now=NOW,
    )
    instance, jobs, _, _ = service(job)
    with pytest.raises(InvalidProductClassificationJobError):
        instance.classify_for_job(job_id=job.job_id)
    assert jobs.updates == []


def test_technical_evidence_failure_marks_running_job_failed() -> None:
    job = make_job()
    failure = ProductClassificationEvidenceLimitExceededError()
    instance, jobs, _, _ = service(job, error=failure)
    with pytest.raises(ProductClassificationEvidenceLimitExceededError):
        instance.classify_for_job(job_id=job.job_id)
    assert jobs.job.status is ProcessingJobStatus.FAILED
    assert jobs.job.error_code == "PRODUCT_CLASSIFICATION_EVIDENCE_LIMIT_EXCEEDED"
