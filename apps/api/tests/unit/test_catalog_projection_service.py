from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.exceptions import (
    CatalogProjectionAlreadyExistsError,
    CatalogProjectionCategoryMismatchError,
    CatalogProjectionCrossProductLineageError,
    CatalogProjectionError,
    CatalogProjectionMaterializationRequiredError,
    CatalogProjectionProductRequiredError,
    CatalogProjectionRepositoryError,
    CatalogProjectionResultStorageError,
    ProcessingJobRepositoryError,
)
from app.domain.catalog_projection import CatalogProjectionStatus
from app.domain.processing_jobs import ProcessingJobStatus
from app.domain.products import ProductCategory
from app.services.catalog_projection import CatalogProjectionService
from app.utils.dynamodb import (
    deserialize_item,
    processing_job_from_item,
    processing_job_to_item,
    serialize_item,
)
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.catalog_projection import (
    catalog_job,
    catalog_product,
    projection_engine,
    reviewed_materialization,
)


class Jobs:
    def __init__(self, job):
        self.job, self.updates = job, []

    def get_by_id(self, job_id):
        return self.job if self.job.job_id == job_id else None

    def update(self, job, expected_version):
        self.updates.append(job)
        self.job = replace(
            job,
            version=expected_version + 1,
            updated_at=NOW + timedelta(seconds=len(self.updates)),
        )
        return self.job


class One:
    def __init__(self, value):
        self.value = value

    def get_by_id(self, _identifier):
        return self.value


class Results:
    value = None

    def get_by_materialization_id(self, _identifier):
        return self.value

    def create(self, value):
        self.value = value
        return value


def setup_service(*, product=None, materialization=None, results=None, jobs_class=Jobs):
    materialization = materialization or reviewed_materialization()
    product = product or catalog_product(materialization)
    job = catalog_job(materialization)
    jobs, stored = jobs_class(job), results or Results()
    service = CatalogProjectionService(
        job_repository=jobs,
        product_repository=One(product),
        materialization_repository=One(materialization),
        result_repository=stored,
        engine=projection_engine(),
        clock=lambda: NOW + timedelta(seconds=10),
    )
    return service, jobs, stored, product, materialization


def test_ready_result_persists_before_completed_and_inputs_remain_unchanged() -> None:
    service, jobs, results, product, materialization = setup_service()
    before = (product, materialization)
    result = service.project_for_job(job_id=jobs.job.job_id)
    assert result.status is CatalogProjectionStatus.READY and results.value is result
    assert [item.status for item in jobs.updates] == [
        ProcessingJobStatus.RUNNING,
        ProcessingJobStatus.COMPLETED,
    ]
    assert jobs.job.progress_percent == 100
    assert jobs.job.result_reference == f"catalog-projection-results/{result.projection_id}"
    assert before == (product, materialization)


def test_job_materialization_lineage_round_trips() -> None:
    _, jobs, _, _, materialization = setup_service()
    item = processing_job_to_item(jobs.job)
    assert item["reviewedAttributeMaterializationId"] == materialization.materialization_id
    assert processing_job_from_item(deserialize_item(serialize_item(item))) == jobs.job


def test_missing_duplicate_and_category_mismatch_fail_before_running() -> None:
    service, jobs, _, _, _ = setup_service()
    service._products = One(None)
    with pytest.raises(CatalogProjectionProductRequiredError):
        service.project_for_job(job_id=jobs.job.job_id)
    assert jobs.updates == []

    service, jobs, _, _, _ = setup_service()
    service._materializations = One(None)
    with pytest.raises(CatalogProjectionMaterializationRequiredError):
        service.project_for_job(job_id=jobs.job.job_id)
    assert jobs.updates == []

    existing = Results()
    existing.value = object()
    service, jobs, _, _, _ = setup_service(results=existing)
    with pytest.raises(CatalogProjectionAlreadyExistsError):
        service.project_for_job(job_id=jobs.job.job_id)
    assert jobs.updates == []

    materialization = reviewed_materialization()
    product = replace(catalog_product(materialization), category=ProductCategory.CENTRIFUGAL_PUMP)
    service, jobs, _, _, _ = setup_service(product=product, materialization=materialization)
    with pytest.raises(CatalogProjectionCategoryMismatchError):
        service.project_for_job(job_id=jobs.job.job_id)
    assert jobs.updates == []

    materialization = reviewed_materialization()
    product = catalog_product(materialization)
    foreign = replace(materialization, product_id=uuid4())
    service, jobs, _, _, _ = setup_service(product=product, materialization=foreign)
    with pytest.raises(CatalogProjectionCrossProductLineageError):
        service.project_for_job(job_id=jobs.job.job_id)
    assert jobs.updates == []


def test_storage_failure_marks_failed() -> None:
    class FailingResults(Results):
        def create(self, value):
            raise CatalogProjectionRepositoryError()

    service, jobs, _, _, _ = setup_service(results=FailingResults())
    with pytest.raises(CatalogProjectionResultStorageError):
        service.project_for_job(job_id=jobs.job.job_id)
    assert jobs.updates[-1].status is ProcessingJobStatus.FAILED

    service, jobs, _, _, _ = setup_service()
    service._engine = SimpleNamespace(
        project=lambda **_: (_ for _ in ()).throw(RuntimeError("technical"))
    )
    with pytest.raises(CatalogProjectionError):
        service.project_for_job(job_id=jobs.job.job_id)
    assert jobs.updates[-1].status is ProcessingJobStatus.FAILED


def test_business_blocked_projection_completes_successfully() -> None:
    materialization = replace(reviewed_materialization(), category=ProductCategory.UNCLASSIFIED)
    product = catalog_product(materialization)
    service, jobs, _, _, _ = setup_service(product=product, materialization=materialization)
    result = service.project_for_job(job_id=jobs.job.job_id)
    assert result.status is CatalogProjectionStatus.BLOCKED
    assert jobs.job.status is ProcessingJobStatus.COMPLETED


def test_completion_failure_preserves_projection_and_logs_risk(caplog) -> None:
    class CompletionFailingJobs(Jobs):
        def update(self, job, expected_version):
            if self.updates:
                raise ProcessingJobRepositoryError()
            return super().update(job, expected_version)

    service, jobs, results, _, _ = setup_service(jobs_class=CompletionFailingJobs)
    with pytest.raises(ProcessingJobRepositoryError):
        service.project_for_job(job_id=jobs.job.job_id)
    assert results.value is not None and jobs.job.status is ProcessingJobStatus.RUNNING
    assert "catalog_projection.completion_consistency_risk" in caplog.text
