"""Catalog enrichment setup, persistence, and lifecycle tests."""

from dataclasses import replace
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import (
    CatalogEnrichmentAlreadyExistsError,
    CatalogEnrichmentCrossProductProjectionError,
    CatalogEnrichmentProductRequiredError,
    CatalogEnrichmentProjectionBlockedError,
    CatalogEnrichmentProjectionRequiredError,
    CatalogEnrichmentProviderTimeoutError,
    CatalogEnrichmentRepositoryError,
    CatalogEnrichmentStorageError,
    ProcessingJobRepositoryError,
)
from app.domain.catalog_enrichment import CatalogEnrichmentResult
from app.domain.catalog_projection import (
    CatalogBlockingReason,
    CatalogProjectionStatus,
    CommerceCatalogProjection,
)
from app.domain.processing_jobs import ProcessingJob, ProcessingJobPage, ProcessingJobStatus
from app.domain.products import Product, ProductPage
from app.services.catalog_enrichment import CatalogEnrichmentService
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.catalog_enrichment import (
    ENRICHMENT_ID,
    FakeLlm,
    enrichment_job,
    enrichment_projection,
    grounded_response,
)
from tests.unit.test_catalog_enrichment_engine import engine


class Jobs:
    def __init__(self, job: ProcessingJob | None, events: list[str]) -> None:
        self.job = job
        self.events = events
        self.completion_error = False

    def get_by_id(self, job_id: UUID) -> ProcessingJob | None:
        return self.job if self.job and self.job.job_id == job_id else None

    def update(self, job: ProcessingJob, expected_version: int) -> ProcessingJob:
        self.events.append(f"job:{job.status.value}")
        if job.status is ProcessingJobStatus.COMPLETED and self.completion_error:
            raise ProcessingJobRepositoryError("unavailable")
        self.job = replace(job, version=expected_version + 1, updated_at=NOW)
        return self.job

    def create(self, job):  # pragma: no cover
        return job

    def list_by_product(self, product_id, *, limit=25, cursor=None):  # pragma: no cover
        return ProcessingJobPage(items=(), next_cursor=None)

    def list_by_source(self, product_id, source_id, *, limit=25, cursor=None):  # pragma: no cover
        return ProcessingJobPage(items=(), next_cursor=None)


class Products:
    def __init__(self, product: Product | None) -> None:
        self.product = product

    def get_by_id(self, product_id: UUID) -> Product | None:
        return self.product

    def create(self, product):  # pragma: no cover
        return product

    def update(self, product, expected_version):  # pragma: no cover
        raise AssertionError("enrichment must not mutate Product")

    def mark_ready_to_publish(self, **kwargs):  # pragma: no cover
        raise AssertionError("enrichment must not mutate Product")

    def list_products(self, *, limit=25, cursor=None):  # pragma: no cover
        return ProductPage(items=(), next_cursor=None)

    def list_by_status(self, status, *, limit=25, cursor=None):  # pragma: no cover
        return ProductPage(items=(), next_cursor=None)

    def delete(self, product_id, expected_version):  # pragma: no cover
        return None


class Projections:
    def __init__(self, projection: CommerceCatalogProjection | None) -> None:
        self.projection = projection

    def get_by_id(self, projection_id: UUID):
        return self.projection

    def create(self, result):  # pragma: no cover
        raise AssertionError("enrichment must not mutate projections")

    def get_by_job_id(self, job_id):  # pragma: no cover
        return None

    def get_by_materialization_id(self, materialization_id):  # pragma: no cover
        return None


class Results:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.items: list[CatalogEnrichmentResult] = []
        self.failure = False

    def create(self, result: CatalogEnrichmentResult) -> CatalogEnrichmentResult:
        self.events.append("result:create")
        if self.failure:
            raise CatalogEnrichmentRepositoryError("unavailable")
        self.items.append(result)
        return result

    def get_by_projection_id(self, projection_id: UUID):
        return tuple(item for item in self.items if item.projection_id == projection_id)

    def get_by_id(self, enrichment_id):  # pragma: no cover
        return None

    def get_by_job_id(self, job_id):  # pragma: no cover
        return None


class FailingLlm:
    provider = "fake"
    model = "grounded-test-model"

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        raise CatalogEnrichmentProviderTimeoutError()


def fixture(*, product=True, projection=True, llm=None):
    actual_product, materialization, actual_projection = enrichment_projection()
    job = enrichment_job(actual_projection)
    events: list[str] = []
    jobs = Jobs(job, events)
    products = Products(actual_product if product else None)
    projections = Projections(actual_projection if projection else None)
    results = Results(events)
    used_llm = llm or FakeLlm([grounded_response(actual_projection)])
    service = CatalogEnrichmentService(
        job_repository=jobs,
        product_repository=products,
        projection_repository=projections,
        result_repository=results,
        engine=engine(used_llm),
        clock=lambda: NOW,
        uuid_factory=lambda: ENRICHMENT_ID,
    )
    return service, jobs, products, projections, results, actual_projection, materialization, events


def test_success_persists_before_completion_and_does_not_mutate_inputs() -> None:
    service, jobs, products, projections, _, projection, materialization, events = fixture()
    product_before = products.product
    result = service.enrich_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]
    assert result.enrichment_id == ENRICHMENT_ID
    assert events == ["job:RUNNING", "result:create", "job:COMPLETED"]
    assert jobs.job and jobs.job.progress_percent == 100
    assert jobs.job.result_reference == f"catalog-enrichment-results/{ENRICHMENT_ID}"
    assert products.product == product_before
    assert projections.projection == projection
    assert materialization.product_id == projection.product_id


def test_ready_with_warnings_succeeds_and_preserves_warning_state() -> None:
    service, jobs, _, projections, _, projection, _, _ = fixture()
    warning_projection = enrichment_projection(manufacturer=None)[2]
    projections.projection = warning_projection
    jobs.job = enrichment_job(warning_projection)
    service._engine._llm.responses = [grounded_response(warning_projection)]  # type: ignore[attr-defined]
    result = service.enrich_for_job(job_id=jobs.job.job_id)
    assert result.warning_codes
    assert projection.product_id == result.product_id


def test_setup_rejections_happen_before_running() -> None:
    service, jobs, _, _, _, _, _, events = fixture(product=False)
    with pytest.raises(CatalogEnrichmentProductRequiredError):
        service.enrich_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]
    assert not events

    service, jobs, _, _, _, _, _, events = fixture(projection=False)
    with pytest.raises(CatalogEnrichmentProjectionRequiredError):
        service.enrich_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]
    assert not events

    service, jobs, products, _, _, _, _, events = fixture()
    assert products.product
    products.product = replace(products.product, product_id=uuid4())
    with pytest.raises(CatalogEnrichmentCrossProductProjectionError):
        service.enrich_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]
    assert not events

    service, jobs, _, projections, _, projection, _, events = fixture()
    projections.projection = replace(
        projection,
        status=CatalogProjectionStatus.BLOCKED,
        blocking_reason_codes=(CatalogBlockingReason.PRODUCT_NAME_MISSING,),
        warning_reason_codes=(),
    )
    with pytest.raises(CatalogEnrichmentProjectionBlockedError):
        service.enrich_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]
    assert not events

    service, jobs, _, _, results, projection, _, events = fixture()
    existing = service.enrich_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]
    jobs.job = enrichment_job(projection)
    events.clear()
    assert results.items == [existing]
    with pytest.raises(CatalogEnrichmentAlreadyExistsError):
        service.enrich_for_job(job_id=jobs.job.job_id)
    assert not events


def test_provider_and_storage_failures_mark_job_failed() -> None:
    service, jobs, _, _, _, _, _, events = fixture(llm=FailingLlm())
    with pytest.raises(CatalogEnrichmentProviderTimeoutError):
        service.enrich_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]
    assert events == ["job:RUNNING", "job:FAILED"]

    service, jobs, _, _, results, _, _, events = fixture()
    results.failure = True
    with pytest.raises(CatalogEnrichmentStorageError):
        service.enrich_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]
    assert events == ["job:RUNNING", "result:create", "job:FAILED"]


def test_completion_failure_preserves_valid_result() -> None:
    service, jobs, _, _, results, _, _, _ = fixture()
    jobs.completion_error = True
    with pytest.raises(ProcessingJobRepositoryError):
        service.enrich_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]
    assert len(results.items) == 1
    assert jobs.job and jobs.job.status is ProcessingJobStatus.RUNNING
