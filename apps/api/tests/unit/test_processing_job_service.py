"""Processing-job application service tests."""

import inspect
from typing import cast
from uuid import UUID

import pytest

from app.core.exceptions import (
    InvalidProcessingJobCursorError,
    ProcessingJobAlreadyExistsError,
    ProcessingJobNotFoundError,
    ProcessingJobRepositoryError,
    ProcessingJobTypeNotSupportedForSourceError,
    ProductNotFoundError,
    ProductRepositoryError,
    ProductSourceNotFoundError,
    ProductSourceRepositoryError,
)
from app.domain.processing_jobs import ProcessingJob, ProcessingJobPage, ProcessingJobType
from app.domain.product_sources import ProductSource, ProductSourcePage, ProductSourceType
from app.domain.products import Product, ProductPage, ProductStatus
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_sources import ProductSourceRepository
from app.repositories.products import ProductRepository
from app.services import processing_jobs as processing_jobs_module
from app.services.processing_jobs import ProcessingJobService
from tests.fixtures.processing_jobs import JOB_ID, make_processing_job
from tests.fixtures.product_sources import SOURCE_ID, make_product_source
from tests.fixtures.products import PRODUCT_ID, SECOND_PRODUCT_ID, make_product


class FakeProducts:
    def __init__(self, product: Product | None, error: Exception | None = None) -> None:
        self.product = product
        self.error = error
        self.get_calls: list[UUID] = []

    def get_by_id(self, product_id: UUID) -> Product | None:
        self.get_calls.append(product_id)
        if self.error:
            raise self.error
        return self.product if self.product and self.product.product_id == product_id else None

    def create(self, product: Product) -> Product:
        raise NotImplementedError

    def update(self, product: Product, expected_version: int) -> Product:
        raise NotImplementedError

    def list_products(self, *, limit: int = 25, cursor: str | None = None) -> ProductPage:
        raise NotImplementedError

    def list_by_status(
        self,
        status: ProductStatus,
        *,
        limit: int = 25,
        cursor: str | None = None,
    ) -> ProductPage:
        raise NotImplementedError

    def delete(self, product_id: UUID, expected_version: int) -> None:
        raise NotImplementedError


class FakeSources:
    def __init__(self, source: ProductSource | None, error: Exception | None = None) -> None:
        self.source = source
        self.error = error
        self.get_calls: list[tuple[UUID, UUID]] = []

    def get_by_id(self, product_id: UUID, source_id: UUID) -> ProductSource | None:
        self.get_calls.append((product_id, source_id))
        if self.error:
            raise self.error
        if self.source and (self.source.product_id, self.source.source_id) == (
            product_id,
            source_id,
        ):
            return self.source
        return None

    def create(self, source: ProductSource) -> ProductSource:
        raise NotImplementedError

    def update(self, source: ProductSource, expected_version: int) -> ProductSource:
        raise NotImplementedError

    def list_by_product(
        self,
        product_id: UUID,
        *,
        limit: int = 25,
        cursor: str | None = None,
    ) -> ProductSourcePage:
        raise NotImplementedError

    def delete(self, product_id: UUID, source_id: UUID, expected_version: int) -> None:
        raise NotImplementedError


class FakeJobs:
    def __init__(
        self,
        *,
        job: ProcessingJob | None = None,
        page: ProcessingJobPage | None = None,
        error: Exception | None = None,
    ) -> None:
        self.job = job
        self.page = page or ProcessingJobPage(items=(), next_cursor=None)
        self.error = error
        self.created: list[ProcessingJob] = []
        self.get_calls: list[UUID] = []
        self.product_lists: list[tuple[UUID, int, str | None]] = []
        self.source_lists: list[tuple[UUID, UUID, int, str | None]] = []

    def create(self, job: ProcessingJob) -> ProcessingJob:
        self.created.append(job)
        if self.error:
            raise self.error
        return job

    def get_by_id(self, job_id: UUID) -> ProcessingJob | None:
        self.get_calls.append(job_id)
        if self.error:
            raise self.error
        return self.job if self.job and self.job.job_id == job_id else None

    def list_by_product(
        self,
        product_id: UUID,
        *,
        limit: int = 25,
        cursor: str | None = None,
    ) -> ProcessingJobPage:
        self.product_lists.append((product_id, limit, cursor))
        if self.error:
            raise self.error
        return self.page

    def list_by_source(
        self,
        product_id: UUID,
        source_id: UUID,
        *,
        limit: int = 25,
        cursor: str | None = None,
    ) -> ProcessingJobPage:
        self.source_lists.append((product_id, source_id, limit, cursor))
        if self.error:
            raise self.error
        return self.page

    def update(self, job: ProcessingJob, expected_version: int) -> ProcessingJob:
        raise NotImplementedError


def build_service(
    products: FakeProducts,
    sources: FakeSources,
    jobs: FakeJobs,
) -> ProcessingJobService:
    return ProcessingJobService(
        cast(ProductRepository, products),
        cast(ProductSourceRepository, sources),
        cast(ProcessingJobRepository, jobs),
    )


def source_of_type(source_type: ProductSourceType) -> ProductSource:
    if source_type is ProductSourceType.TEXT:
        return make_product_source(
            source_type=source_type,
            original_filename=None,
            mime_type="text/plain",
            text_content="source text",
        )
    if source_type is ProductSourceType.IMAGE:
        return make_product_source(
            source_type=source_type,
            original_filename="nameplate.png",
            mime_type="image/png",
        )
    if source_type is ProductSourceType.CSV:
        return make_product_source(
            source_type=source_type,
            original_filename="catalog.csv",
            mime_type="text/csv",
        )
    return make_product_source(source_type=source_type)


@pytest.mark.parametrize(
    ("source_type", "job_type"),
    [
        (ProductSourceType.TEXT, ProcessingJobType.SOURCE_PROCESSING),
        (ProductSourceType.PDF, ProcessingJobType.PDF_TEXT_EXTRACTION),
        (ProductSourceType.PDF, ProcessingJobType.PDF_TABLE_EXTRACTION),
        (ProductSourceType.IMAGE, ProcessingJobType.IMAGE_ANALYSIS),
        (ProductSourceType.IMAGE, ProcessingJobType.IMAGE_OCR),
        (ProductSourceType.CSV, ProcessingJobType.CSV_PROCESSING),
    ],
)
def test_create_supported_job_uses_domain_defaults(
    source_type: ProductSourceType, job_type: ProcessingJobType
) -> None:
    products = FakeProducts(make_product())
    sources = FakeSources(source_of_type(source_type))
    jobs = FakeJobs()
    created = build_service(products, sources, jobs).create_job(
        product_id=PRODUCT_ID, source_id=SOURCE_ID, job_type=job_type
    )
    assert products.get_calls == [PRODUCT_ID]
    assert sources.get_calls == [(PRODUCT_ID, SOURCE_ID)]
    assert jobs.created == [created]
    assert (created.status.value, created.attempt, created.progress_percent, created.version) == (
        "PENDING",
        1,
        0,
        1,
    )
    assert created.started_at is created.completed_at is None
    assert created.error_code is created.error_message is created.result_reference is None


def test_missing_product_stops_source_and_job_calls() -> None:
    sources, jobs = FakeSources(make_product_source()), FakeJobs()
    with pytest.raises(ProductNotFoundError):
        build_service(FakeProducts(None), sources, jobs).create_job(
            product_id=PRODUCT_ID,
            source_id=SOURCE_ID,
            job_type=ProcessingJobType.SOURCE_PROCESSING,
        )
    assert sources.get_calls == [] and jobs.created == []


def test_missing_or_cross_product_source_stops_job_creation() -> None:
    for source in (None, make_product_source(product_id=SECOND_PRODUCT_ID)):
        jobs = FakeJobs()
        with pytest.raises(ProductSourceNotFoundError):
            build_service(FakeProducts(make_product()), FakeSources(source), jobs).create_job(
                product_id=PRODUCT_ID,
                source_id=SOURCE_ID,
                job_type=ProcessingJobType.SOURCE_PROCESSING,
            )
        assert jobs.created == []


def test_incompatible_type_is_rejected_before_job_repository() -> None:
    jobs = FakeJobs()
    with pytest.raises(ProcessingJobTypeNotSupportedForSourceError) as captured:
        build_service(
            FakeProducts(make_product()),
            FakeSources(source_of_type(ProductSourceType.IMAGE)),
            jobs,
        ).create_job(
            product_id=PRODUCT_ID,
            source_id=SOURCE_ID,
            job_type=ProcessingJobType.PDF_TEXT_EXTRACTION,
        )
    assert captured.value.source_type == "IMAGE"
    assert captured.value.job_type == "PDF_TEXT_EXTRACTION"
    assert jobs.created == []


@pytest.mark.parametrize(
    "error",
    [ProcessingJobAlreadyExistsError("duplicate"), ProcessingJobRepositoryError("failure")],
)
def test_create_preserves_controlled_job_repository_errors(error: Exception) -> None:
    with pytest.raises(type(error)):
        build_service(
            FakeProducts(make_product()), FakeSources(make_product_source()), FakeJobs(error=error)
        ).create_job(
            product_id=PRODUCT_ID,
            source_id=SOURCE_ID,
            job_type=ProcessingJobType.SOURCE_PROCESSING,
        )


def test_retrieve_returns_job_or_controlled_not_found() -> None:
    job = make_processing_job()
    jobs = FakeJobs(job=job)
    assert build_service(FakeProducts(None), FakeSources(None), jobs).get_job(job_id=JOB_ID) == job
    assert jobs.get_calls == [JOB_ID]
    with pytest.raises(ProcessingJobNotFoundError) as captured:
        build_service(FakeProducts(None), FakeSources(None), FakeJobs()).get_job(job_id=JOB_ID)
    assert captured.value.job_id == str(JOB_ID)


def test_retrieve_preserves_repository_failure() -> None:
    with pytest.raises(ProcessingJobRepositoryError):
        build_service(
            FakeProducts(None), FakeSources(None), FakeJobs(error=ProcessingJobRepositoryError())
        ).get_job(job_id=JOB_ID)


def test_product_list_validates_parent_and_preserves_page() -> None:
    job = make_processing_job()
    jobs = FakeJobs(page=ProcessingJobPage(items=(job,), next_cursor="next"))
    result = build_service(FakeProducts(make_product()), FakeSources(None), jobs).list_product_jobs(
        product_id=PRODUCT_ID, limit=7, cursor="current"
    )
    assert jobs.product_lists == [(PRODUCT_ID, 7, "current")]
    assert result.items[0].job_id == JOB_ID and result.next_cursor == "next"


def test_missing_product_stops_product_list() -> None:
    jobs = FakeJobs()
    with pytest.raises(ProductNotFoundError):
        build_service(FakeProducts(None), FakeSources(None), jobs).list_product_jobs(
            product_id=PRODUCT_ID, limit=20
        )
    assert jobs.product_lists == []


def test_source_list_validates_scoped_parent_and_passes_pagination() -> None:
    jobs = FakeJobs(page=ProcessingJobPage(items=(), next_cursor=None))
    result = build_service(
        FakeProducts(make_product()), FakeSources(make_product_source()), jobs
    ).list_source_jobs(product_id=PRODUCT_ID, source_id=SOURCE_ID, limit=5, cursor="opaque")
    assert jobs.source_lists == [(PRODUCT_ID, SOURCE_ID, 5, "opaque")]
    assert result.model_dump(by_alias=True) == {"items": [], "nextCursor": None}


def test_cross_product_source_stops_source_list() -> None:
    jobs = FakeJobs()
    with pytest.raises(ProductSourceNotFoundError):
        build_service(
            FakeProducts(make_product()),
            FakeSources(make_product_source(product_id=SECOND_PRODUCT_ID)),
            jobs,
        ).list_source_jobs(product_id=PRODUCT_ID, source_id=SOURCE_ID, limit=20)
    assert jobs.source_lists == []


@pytest.mark.parametrize(
    "error",
    [
        ProductRepositoryError("product"),
        ProductSourceRepositoryError("source"),
        InvalidProcessingJobCursorError("cursor"),
    ],
)
def test_read_failures_are_preserved(error: Exception) -> None:
    products = FakeProducts(
        make_product(), error if isinstance(error, ProductRepositoryError) else None
    )
    sources = FakeSources(
        make_product_source(), error if isinstance(error, ProductSourceRepositoryError) else None
    )
    jobs = FakeJobs(error=error if isinstance(error, InvalidProcessingJobCursorError) else None)
    with pytest.raises(type(error)):
        build_service(products, sources, jobs).list_source_jobs(
            product_id=PRODUCT_ID, source_id=SOURCE_ID, limit=20, cursor="bad"
        )


def test_service_has_no_http_infrastructure_storage_or_execution_imports() -> None:
    source = inspect.getsource(processing_jobs_module).lower()
    for forbidden in ("fastapi", "boto3", "objectstorage", "worker", "parser", "ocr", "openai"):
        assert forbidden not in source
