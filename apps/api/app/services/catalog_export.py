"""Product-level catalog export orchestration with storage compensation."""

import io
import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.exceptions import (
    CatalogExportAlreadyExistsError,
    CatalogExportCrossProductProjectionError,
    CatalogExportError,
    CatalogExportLineageInvalidError,
    CatalogExportProductRequiredError,
    CatalogExportProjectionBlockedError,
    CatalogExportProjectionRequiredError,
    CatalogExportRepositoryError,
    CatalogExportResultStorageError,
    CatalogExportStorageError,
    CatalogProjectionRepositoryError,
    InvalidCatalogExportJobError,
    ObjectStorageError,
    ProcessingJobRepositoryError,
    ProductRepositoryError,
)
from app.domain.catalog_export import CatalogExportResult, CatalogExportStatus
from app.domain.catalog_projection import CatalogProjectionStatus, CommerceCatalogProjection
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.domain.products import Product
from app.repositories.catalog_export import CatalogExportResultRepository
from app.repositories.catalog_projection import CommerceCatalogProjectionRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.products import ProductRepository
from app.services.catalog_export_package_builder import CatalogExportPackageBuilder
from app.storage.protocol import ObjectStorage

logger = logging.getLogger(__name__)


class CatalogExportService:
    def __init__(
        self,
        *,
        job_repository: ProcessingJobRepository,
        product_repository: ProductRepository,
        projection_repository: CommerceCatalogProjectionRepository,
        result_repository: CatalogExportResultRepository,
        object_storage: ObjectStorage,
        package_builder: CatalogExportPackageBuilder,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self._jobs = job_repository
        self._products = product_repository
        self._projections = projection_repository
        self._results = result_repository
        self._storage = object_storage
        self._builder = package_builder
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid = uuid_factory or uuid4

    def export_for_job(self, *, job_id: UUID) -> CatalogExportResult:
        job = self._jobs.get_by_id(job_id)
        if (
            job is None
            or job.job_type is not ProcessingJobType.CATALOG_EXPORT
            or job.status is not ProcessingJobStatus.PENDING
            or job.source_id is not None
            or job.projection_id is None
        ):
            raise InvalidCatalogExportJobError()
        product, projection = self._validate_setup(job)
        running = self._jobs.update(
            transition_processing_job(job, ProcessingJobStatus.RUNNING, now=self._clock()),
            expected_version=job.version,
        )
        export_id = self._uuid()
        created_at = self._clock().astimezone(UTC)
        saved_keys: list[str] = []
        logger.info(
            "event=catalog_export.started job_id=%s product_id=%s projection_id=%s "
            "export_id=%s projection_status=%s product_version=%s",
            job.job_id,
            product.product_id,
            projection.projection_id,
            export_id,
            projection.status.value,
            product.version,
        )
        try:
            package = self._builder.build(
                export_id=export_id,
                projection=projection,
                created_at=created_at,
            )
            logger.info(
                "event=catalog_export.package_built job_id=%s export_id=%s warning_count=%s",
                job.job_id,
                export_id,
                len(projection.warning_reason_codes),
            )
            for artifact in package.artifacts:
                stored = self._storage.save(
                    object_key=artifact.object_key,
                    stream=io.BytesIO(package.content_for(artifact.format)),
                    max_size_bytes=self._builder.max_size_for(artifact.format),
                )
                saved_keys.append(artifact.object_key)
                if (
                    stored.object_key != artifact.object_key
                    or stored.size_bytes != artifact.size_bytes
                    or stored.checksum_sha256 != artifact.sha256
                ):
                    raise CatalogExportStorageError()
                logger.info(
                    "event=catalog_export.artifact_saved job_id=%s export_id=%s format=%s "
                    "size_bytes=%s checksum_prefix=%s",
                    job.job_id,
                    export_id,
                    artifact.format.value,
                    artifact.size_bytes,
                    artifact.sha256[:12],
                )
            result = CatalogExportResult(
                export_id=export_id,
                job_id=job.job_id,
                product_id=projection.product_id,
                projection_id=projection.projection_id,
                projection_product_version=projection.product_version,
                category=projection.category,
                schema_version=projection.schema_version,
                schema_fingerprint=projection.schema_fingerprint,
                projection_status=projection.status,
                status=CatalogExportStatus.EXPORTED,
                artifacts=package.artifacts,
                warning_reason_codes=projection.warning_reason_codes,
                engine="deterministic-catalog-exporter-v1",
                engine_version="1.0",
                created_at=created_at,
            )
            stored_result = self._results.create(result)
        except CatalogExportError as exc:
            self._cleanup(saved_keys, job=job, export_id=export_id)
            self._fail(running, exc)
            raise
        except ObjectStorageError as exc:
            storage_error = CatalogExportStorageError()
            self._cleanup(saved_keys, job=job, export_id=export_id)
            self._fail(running, storage_error)
            raise storage_error from exc
        except CatalogExportRepositoryError as exc:
            result_error = CatalogExportResultStorageError()
            self._cleanup(saved_keys, job=job, export_id=export_id)
            self._fail(running, result_error)
            raise result_error from exc
        except Exception as exc:
            engine_error = CatalogExportError()
            self._cleanup(saved_keys, job=job, export_id=export_id)
            self._fail(running, engine_error)
            raise engine_error from exc
        completed = transition_processing_job(
            replace(
                running,
                result_reference=f"catalog-export-results/{stored_result.export_id}",
            ),
            ProcessingJobStatus.COMPLETED,
            now=self._clock(),
        )
        try:
            self._jobs.update(completed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.error(
                "event=catalog_export.completion_consistency_risk job_id=%s export_id=%s",
                job.job_id,
                stored_result.export_id,
            )
            raise
        logger.info(
            "event=catalog_export.completed job_id=%s export_id=%s projection_id=%s "
            "artifact_count=%s warning_count=%s",
            job.job_id,
            stored_result.export_id,
            stored_result.projection_id,
            len(stored_result.artifacts),
            len(stored_result.warning_reason_codes),
        )
        return stored_result

    def _validate_setup(self, job: ProcessingJob) -> tuple[Product, CommerceCatalogProjection]:
        try:
            product = self._products.get_by_id(job.product_id)
            if product is None:
                raise CatalogExportProductRequiredError()
            assert job.projection_id is not None
            projection = self._projections.get_by_id(job.projection_id)
            if projection is None:
                raise CatalogExportProjectionRequiredError()
            if projection.product_id != product.product_id:
                raise CatalogExportCrossProductProjectionError()
            if projection.status is CatalogProjectionStatus.BLOCKED:
                raise CatalogExportProjectionBlockedError()
            if (
                projection.status
                not in {
                    CatalogProjectionStatus.READY,
                    CatalogProjectionStatus.READY_WITH_WARNINGS,
                }
                or projection.category != product.category
                or projection.attribute_count != len(projection.attributes)
                or len(projection.schema_fingerprint) != 64
            ):
                raise CatalogExportLineageInvalidError()
            if self._results.get_by_projection_id(projection.projection_id):
                raise CatalogExportAlreadyExistsError()
            return product, projection
        except CatalogExportError:
            raise
        except CatalogExportRepositoryError as exc:
            raise CatalogExportResultStorageError() from exc
        except (ProductRepositoryError, CatalogProjectionRepositoryError) as exc:
            raise CatalogExportLineageInvalidError() from exc

    def _cleanup(self, object_keys: list[str], *, job: ProcessingJob, export_id: UUID) -> None:
        if not object_keys:
            return
        logger.info(
            "event=catalog_export.cleanup_started job_id=%s export_id=%s object_count=%s",
            job.job_id,
            export_id,
            len(object_keys),
        )
        for object_key in reversed(object_keys):
            try:
                self._storage.delete(object_key)
            except ObjectStorageError:
                logger.warning(
                    "event=catalog_export.cleanup_failed job_id=%s export_id=%s",
                    job.job_id,
                    export_id,
                )

    def _fail(self, running: ProcessingJob, error: CatalogExportError) -> None:
        logger.warning(
            "event=catalog_export.failed job_id=%s error_code=%s",
            running.job_id,
            error.code,
        )
        failed = transition_processing_job(
            replace(running, error_code=error.code, error_message=error.safe_message),
            ProcessingJobStatus.FAILED,
            now=self._clock(),
        )
        try:
            self._jobs.update(failed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.exception(
                "event=catalog_export.completion_consistency_risk job_id=%s",
                running.job_id,
            )
