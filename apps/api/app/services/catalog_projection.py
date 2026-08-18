"""Product-level commerce catalog projection orchestration."""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import (
    CatalogProjectionAlreadyExistsError,
    CatalogProjectionCategoryMismatchError,
    CatalogProjectionCrossProductLineageError,
    CatalogProjectionError,
    CatalogProjectionLineageInvalidError,
    CatalogProjectionMaterializationRequiredError,
    CatalogProjectionProductRequiredError,
    CatalogProjectionRepositoryError,
    CatalogProjectionResultStorageError,
    InvalidCatalogProjectionJobError,
    ProcessingJobRepositoryError,
    ProductRepositoryError,
    ReviewedAttributeRepositoryError,
)
from app.domain.catalog_projection import CommerceCatalogProjection
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.domain.reviewed_attributes import ReviewedAttributeSetStatus
from app.repositories.catalog_projection import CommerceCatalogProjectionRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.products import ProductRepository
from app.repositories.reviewed_attributes import FinalReviewedAttributeRepository
from app.services.catalog_projection_engine import CatalogProjectionEngine

logger = logging.getLogger(__name__)


class CatalogProjectionService:
    def __init__(
        self,
        *,
        job_repository: ProcessingJobRepository,
        product_repository: ProductRepository,
        materialization_repository: FinalReviewedAttributeRepository,
        result_repository: CommerceCatalogProjectionRepository,
        engine: CatalogProjectionEngine,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._jobs = job_repository
        self._products = product_repository
        self._materializations = materialization_repository
        self._results = result_repository
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(UTC))

    def project_for_job(self, *, job_id: UUID) -> CommerceCatalogProjection:
        job = self._jobs.get_by_id(job_id)
        if (
            job is None
            or job.job_type is not ProcessingJobType.CATALOG_PROJECTION
            or job.status is not ProcessingJobStatus.PENDING
            or job.source_id is not None
            or job.reviewed_attribute_materialization_id is None
        ):
            raise InvalidCatalogProjectionJobError()
        try:
            product = self._products.get_by_id(job.product_id)
            if product is None:
                raise CatalogProjectionProductRequiredError()
            if product.product_id != job.product_id:
                raise CatalogProjectionCrossProductLineageError()
            materialization = self._materializations.get_by_id(
                job.reviewed_attribute_materialization_id
            )
            if materialization is None:
                raise CatalogProjectionMaterializationRequiredError()
            if materialization.product_id != product.product_id:
                raise CatalogProjectionCrossProductLineageError()
            if materialization.category != product.category:
                raise CatalogProjectionCategoryMismatchError()
            if (
                materialization.status is not ReviewedAttributeSetStatus.MATERIALIZED
                or materialization.materialized_required_count
                != materialization.required_attribute_count
                or materialization.attribute_count != len(materialization.attributes)
                or len(materialization.schema_fingerprint) != 64
            ):
                raise CatalogProjectionLineageInvalidError()
            if self._results.get_by_materialization_id(materialization.materialization_id):
                raise CatalogProjectionAlreadyExistsError()
        except CatalogProjectionError:
            raise
        except (
            ProductRepositoryError,
            ReviewedAttributeRepositoryError,
            CatalogProjectionRepositoryError,
        ) as exc:
            raise CatalogProjectionLineageInvalidError() from exc
        running = self._jobs.update(
            transition_processing_job(job, ProcessingJobStatus.RUNNING, now=self._clock()),
            expected_version=job.version,
        )
        logger.info(
            "event=catalog_projection.started job_id=%s product_id=%s product_version=%s "
            "materialization_id=%s category=%s",
            job.job_id,
            product.product_id,
            product.version,
            materialization.materialization_id,
            product.category.value,
        )
        try:
            result = self._engine.project(
                job_id=job.job_id,
                product=product,
                materialization=materialization,
                now=self._clock(),
            )
            stored = self._results.create(result)
        except CatalogProjectionError as exc:
            self._fail(running, exc)
            raise
        except CatalogProjectionRepositoryError as exc:
            storage_error = CatalogProjectionResultStorageError()
            self._fail(running, storage_error)
            raise storage_error from exc
        except Exception as exc:
            generic_error = CatalogProjectionError()
            self._fail(running, generic_error)
            raise generic_error from exc
        completed = transition_processing_job(
            replace(
                running,
                result_reference=f"catalog-projection-results/{stored.projection_id}",
            ),
            ProcessingJobStatus.COMPLETED,
            now=self._clock(),
        )
        try:
            self._jobs.update(completed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.error(
                "event=catalog_projection.completion_consistency_risk job_id=%s projection_id=%s",
                job.job_id,
                stored.projection_id,
            )
            raise
        logger.info(
            "event=catalog_projection.completed job_id=%s projection_id=%s status=%s "
            "attribute_count=%s blocker_count=%s warning_count=%s",
            job.job_id,
            stored.projection_id,
            stored.status.value,
            stored.attribute_count,
            len(stored.blocking_reason_codes),
            len(stored.warning_reason_codes),
        )
        return stored

    def _fail(self, running: ProcessingJob, error: CatalogProjectionError) -> None:
        failed = transition_processing_job(
            replace(running, error_code=error.code, error_message=error.safe_message),
            ProcessingJobStatus.FAILED,
            now=self._clock(),
        )
        try:
            self._jobs.update(failed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.exception(
                "event=catalog_projection.completion_consistency_risk job_id=%s",
                running.job_id,
            )
