"""Catalog export orchestration, compensation, and lifecycle tests."""

import hashlib
import io
from dataclasses import replace
from typing import cast
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import (
    CatalogExportAlreadyExistsError,
    CatalogExportCrossProductProjectionError,
    CatalogExportJsonSizeLimitExceededError,
    CatalogExportLineageInvalidError,
    CatalogExportProductRequiredError,
    CatalogExportProjectionBlockedError,
    CatalogExportProjectionRequiredError,
    CatalogExportRepositoryError,
    CatalogExportResultStorageError,
    CatalogExportStorageError,
    InvalidCatalogExportJobError,
    ObjectStorageError,
    ProcessingJobRepositoryError,
)
from app.domain.catalog_export import CatalogExportResult
from app.domain.catalog_projection import (
    CatalogBlockingReason,
    CatalogProjectionStatus,
    CommerceCatalogProjection,
)
from app.domain.processing_jobs import ProcessingJob, ProcessingJobPage, ProcessingJobStatus
from app.domain.products import Product, ProductPage
from app.repositories.catalog_export import CatalogExportResultRepository
from app.repositories.catalog_projection import CommerceCatalogProjectionRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.products import ProductRepository
from app.services.catalog_export import CatalogExportService
from app.storage.models import StoredObject
from app.storage.protocol import ObjectStorage
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.catalog_export import EXPORT_ID, export_job, export_result, package_builder


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
            raise ProcessingJobRepositoryError("completion unavailable")
        self.job = replace(job, version=expected_version + 1, updated_at=NOW)
        return self.job

    def create(self, job):  # pragma: no cover - protocol-only
        return job

    def list_by_product(self, product_id, *, limit=25, cursor=None):  # pragma: no cover
        return ProcessingJobPage(items=(), next_cursor=None)

    def list_by_source(self, product_id, source_id, *, limit=25, cursor=None):  # pragma: no cover
        return ProcessingJobPage(items=(), next_cursor=None)


class Products:
    def __init__(self, product: Product | None) -> None:
        self.product = product

    def get_by_id(self, product_id: UUID) -> Product | None:
        return self.product if self.product and self.product.product_id == product_id else None

    def create(self, product):  # pragma: no cover - protocol-only
        return product

    def update(self, product, expected_version):  # pragma: no cover
        return product

    def mark_ready_to_publish(self, **kwargs):  # pragma: no cover
        raise AssertionError("export must not mutate Product")

    def list_products(self, *, limit=25, cursor=None):  # pragma: no cover
        return ProductPage(items=(), next_cursor=None)

    def list_by_status(self, status, *, limit=25, cursor=None):  # pragma: no cover
        return ProductPage(items=(), next_cursor=None)

    def delete(self, product_id, expected_version):  # pragma: no cover
        return None


class Projections:
    def __init__(self, projection: CommerceCatalogProjection | None) -> None:
        self.projection = projection

    def get_by_id(self, projection_id: UUID) -> CommerceCatalogProjection | None:
        return (
            self.projection
            if self.projection and self.projection.projection_id == projection_id
            else None
        )

    def create(self, result):  # pragma: no cover
        return result

    def get_by_job_id(self, job_id):  # pragma: no cover
        return None

    def get_by_materialization_id(self, materialization_id):  # pragma: no cover
        return None


class Results:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.result: CatalogExportResult | None = None
        self.duplicate = False
        self.create_error: Exception | None = None

    def get_by_projection_id(self, projection_id: UUID) -> CatalogExportResult | None:
        return self.result if self.duplicate else None

    def create(self, result: CatalogExportResult) -> CatalogExportResult:
        self.events.append("result:create")
        if self.create_error:
            raise self.create_error
        self.result = result
        return result

    def get_by_id(self, export_id):  # pragma: no cover
        return self.result

    def get_by_job_id(self, job_id):  # pragma: no cover
        return self.result


class Storage:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.content: dict[str, bytes] = {}
        self.deleted: list[str] = []
        self.fail_on_save: int | None = None
        self.cleanup_error = False
        self.saves = 0

    def save(self, *, object_key: str, stream: io.BytesIO, max_size_bytes: int) -> StoredObject:
        self.saves += 1
        self.events.append(f"storage:save:{self.saves}")
        if self.fail_on_save == self.saves:
            raise ObjectStorageError("write failed")
        content = stream.read()
        assert len(content) <= max_size_bytes
        self.content[object_key] = content
        return StoredObject(
            object_key=object_key,
            size_bytes=len(content),
            checksum_sha256=hashlib.sha256(content).hexdigest(),
            created_at=NOW,
        )

    def delete(self, object_key: str) -> None:
        self.events.append("storage:delete")
        self.deleted.append(object_key)
        if self.cleanup_error:
            raise ObjectStorageError("cleanup failed")
        self.content.pop(object_key, None)

    def open(self, object_key):  # pragma: no cover
        return io.BytesIO(self.content[object_key])

    def exists(self, object_key):  # pragma: no cover
        return object_key in self.content

    def get_metadata(self, object_key):  # pragma: no cover
        raise NotImplementedError


def _fixture(*, product=None, projection=None, builder=None):
    default_product, default_projection, _, _ = export_result()
    product = default_product if product is None else product
    projection = default_projection if projection is None else projection
    events: list[str] = []
    jobs = Jobs(replace(export_job(projection), product_id=product.product_id), events)
    results = Results(events)
    storage = Storage(events)
    service = CatalogExportService(
        job_repository=cast(ProcessingJobRepository, jobs),
        product_repository=cast(ProductRepository, Products(product)),
        projection_repository=cast(CommerceCatalogProjectionRepository, Projections(projection)),
        result_repository=cast(CatalogExportResultRepository, results),
        object_storage=cast(ObjectStorage, storage),
        package_builder=builder or package_builder(),
        clock=lambda: NOW,
        uuid_factory=lambda: EXPORT_ID,
    )
    return service, jobs, results, storage, events, product, projection


def test_ready_export_writes_three_objects_persists_then_completes() -> None:
    service, jobs, results, storage, events, product, projection = _fixture()
    original_product, original_projection = product, projection
    result = service.export_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]
    assert result is results.result
    assert len(storage.content) == 3
    assert events == [
        "job:RUNNING",
        "storage:save:1",
        "storage:save:2",
        "storage:save:3",
        "result:create",
        "job:COMPLETED",
    ]
    assert jobs.job is not None and jobs.job.status is ProcessingJobStatus.COMPLETED
    assert jobs.job.result_reference == f"catalog-export-results/{EXPORT_ID}"
    assert product == original_product and projection == original_projection


def test_ready_with_warnings_exports_and_preserves_warning_everywhere() -> None:
    product, projection, _, _ = export_result(manufacturer=None)
    service, jobs, _, storage, _, _, _ = _fixture(product=product, projection=projection)
    result = service.export_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]
    assert [item.value for item in result.warning_reason_codes] == ["MANUFACTURER_MISSING"]
    assert b"MANUFACTURER_MISSING" in storage.content[result.artifacts[0].object_key]
    assert b"MANUFACTURER_MISSING" in storage.content[result.artifacts[1].object_key]
    assert b"MANUFACTURER_MISSING" in storage.content[result.artifacts[2].object_key]


def test_blocked_projection_is_rejected_before_running_or_storage() -> None:
    product, projection, _, _ = export_result()
    blocked = replace(
        projection,
        status=CatalogProjectionStatus.BLOCKED,
        blocking_reason_codes=(CatalogBlockingReason.REQUIRED_ATTRIBUTE_MISSING,),
    )
    service, jobs, _, storage, events, _, _ = _fixture(product=product, projection=blocked)
    with pytest.raises(CatalogExportProjectionBlockedError):
        service.export_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]
    assert events == [] and storage.content == {}


def test_stale_projection_is_allowed_but_category_mismatch_is_not() -> None:
    product, projection, _, _ = export_result()
    service, jobs, _, _, _, _, _ = _fixture(
        product=replace(product, version=99), projection=projection
    )
    assert service.export_for_job(job_id=jobs.job.job_id).projection_product_version == 3  # type: ignore[union-attr]
    wrong_category = replace(product, category=product.category.__class__.CENTRIFUGAL_PUMP)
    service, jobs, _, _, _, _, _ = _fixture(product=wrong_category, projection=projection)
    with pytest.raises(CatalogExportLineageInvalidError):
        service.export_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]


def test_missing_product_projection_cross_product_duplicate_and_invalid_job() -> None:
    product, projection, _, existing = export_result()
    service, jobs, _, _, _, _, _ = _fixture()
    service._products = cast(ProductRepository, Products(None))
    with pytest.raises(CatalogExportProductRequiredError):
        service.export_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]

    service, jobs, _, _, _, _, _ = _fixture()
    service._projections = cast(CommerceCatalogProjectionRepository, Projections(None))
    with pytest.raises(CatalogExportProjectionRequiredError):
        service.export_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]

    other = replace(projection, product_id=uuid4())
    service, jobs, _, _, _, _, _ = _fixture(product=product, projection=other)
    with pytest.raises(CatalogExportCrossProductProjectionError):
        service.export_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]

    service, jobs, results, _, _, _, _ = _fixture()
    results.result, results.duplicate = existing, True
    with pytest.raises(CatalogExportAlreadyExistsError):
        service.export_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]

    jobs.job = None
    with pytest.raises(InvalidCatalogExportJobError):
        service.export_for_job(job_id=uuid4())


@pytest.mark.parametrize("fail_on", [1, 2, 3])
def test_partial_storage_failures_cleanup_every_saved_object_and_fail_job(fail_on: int) -> None:
    service, jobs, _, storage, _, _, _ = _fixture()
    storage.fail_on_save = fail_on
    with pytest.raises(CatalogExportStorageError):
        service.export_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]
    assert len(storage.deleted) == fail_on - 1
    assert storage.content == {}
    assert jobs.job is not None and jobs.job.status is ProcessingJobStatus.FAILED
    assert jobs.job.error_code == "CATALOG_EXPORT_STORAGE_FAILED"


def test_result_persistence_failure_cleans_all_objects_and_fails_job() -> None:
    service, jobs, results, storage, events, _, _ = _fixture()
    results.create_error = CatalogExportRepositoryError("ddb unavailable")
    with pytest.raises(CatalogExportResultStorageError):
        service.export_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]
    assert len(storage.deleted) == 3 and storage.content == {}
    assert events.index("result:create") < events.index("storage:delete")
    assert jobs.job is not None and jobs.job.status is ProcessingJobStatus.FAILED


def test_cleanup_failure_is_suppressed_but_original_failure_remains() -> None:
    service, jobs, results, storage, _, _, _ = _fixture()
    results.create_error = CatalogExportRepositoryError()
    storage.cleanup_error = True
    with pytest.raises(CatalogExportResultStorageError):
        service.export_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]
    assert len(storage.deleted) == 3


def test_builder_failure_marks_job_failed_without_storage() -> None:
    service, jobs, _, storage, _, _, _ = _fixture(builder=package_builder(json_limit=1))
    with pytest.raises(CatalogExportJsonSizeLimitExceededError):
        service.export_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]
    assert storage.content == {}
    assert jobs.job is not None and jobs.job.status is ProcessingJobStatus.FAILED


def test_completion_failure_preserves_valid_result_and_objects() -> None:
    service, jobs, results, storage, _, _, _ = _fixture()
    jobs.completion_error = True
    with pytest.raises(ProcessingJobRepositoryError):
        service.export_for_job(job_id=jobs.job.job_id)  # type: ignore[union-attr]
    assert results.result is not None and len(storage.content) == 3
    assert storage.deleted == []
