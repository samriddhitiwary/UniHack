"""Product-level grounded catalog enrichment orchestration."""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.exceptions import (
    CatalogEnrichmentAlreadyExistsError,
    CatalogEnrichmentCrossProductProjectionError,
    CatalogEnrichmentError,
    CatalogEnrichmentLineageInvalidError,
    CatalogEnrichmentProductRequiredError,
    CatalogEnrichmentProjectionBlockedError,
    CatalogEnrichmentProjectionRequiredError,
    CatalogEnrichmentRepositoryError,
    CatalogEnrichmentStorageError,
    CatalogProjectionRepositoryError,
    InvalidCatalogEnrichmentJobError,
    ProcessingJobRepositoryError,
    ProductRepositoryError,
)
from app.domain.catalog_enrichment import CatalogEnrichmentResult
from app.domain.catalog_projection import CatalogProjectionStatus, CommerceCatalogProjection
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.repositories.catalog_enrichment import CatalogEnrichmentResultRepository
from app.repositories.catalog_projection import CommerceCatalogProjectionRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.products import ProductRepository
from app.services.catalog_enrichment_engine import (
    CatalogEnrichmentEngine,
    CatalogEnrichmentPreparation,
)

logger = logging.getLogger(__name__)


class CatalogEnrichmentService:
    def __init__(
        self,
        *,
        job_repository: ProcessingJobRepository,
        product_repository: ProductRepository,
        projection_repository: CommerceCatalogProjectionRepository,
        result_repository: CatalogEnrichmentResultRepository,
        engine: CatalogEnrichmentEngine,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self._jobs = job_repository
        self._products = product_repository
        self._projections = projection_repository
        self._results = result_repository
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid = uuid_factory or uuid4

    def enrich_for_job(self, *, job_id: UUID) -> CatalogEnrichmentResult:
        job = self._jobs.get_by_id(job_id)
        if (
            job is None
            or job.job_type is not ProcessingJobType.AI_CATALOG_ENRICHMENT
            or job.status is not ProcessingJobStatus.PENDING
            or job.source_id is not None
            or job.projection_id is None
        ):
            raise InvalidCatalogEnrichmentJobError()
        projection, preparation = self._validate_setup(job)
        running = self._jobs.update(
            transition_processing_job(job, ProcessingJobStatus.RUNNING, now=self._clock()),
            expected_version=job.version,
        )
        enrichment_id = self._uuid()
        logger.info(
            "event=catalog_enrichment.started job_id=%s product_id=%s projection_id=%s "
            "enrichment_id=%s provider=%s model=%s prompt_version=%s fact_count=%s",
            job.job_id,
            job.product_id,
            projection.projection_id,
            enrichment_id,
            self._engine.provider,
            self._engine.model,
            preparation.prompt.prompt_version,
            len(preparation.facts.facts),
        )
        try:
            logger.info(
                "event=catalog_enrichment.provider_called job_id=%s enrichment_id=%s provider=%s",
                job.job_id,
                enrichment_id,
                self._engine.provider,
            )
            result = self._engine.generate(
                preparation=preparation,
                projection=projection,
                job_id=job.job_id,
                enrichment_id=enrichment_id,
                created_at=self._clock().astimezone(UTC),
            )
            stored = self._results.create(result)
        except CatalogEnrichmentRepositoryError as exc:
            error: CatalogEnrichmentError = CatalogEnrichmentStorageError()
            self._fail(running, error)
            raise error from exc
        except CatalogEnrichmentError as exc:
            self._fail(running, exc)
            raise
        except Exception as exc:
            error = CatalogEnrichmentError()
            self._fail(running, error)
            raise error from exc
        completed = transition_processing_job(
            replace(
                running,
                result_reference=f"catalog-enrichment-results/{stored.enrichment_id}",
            ),
            ProcessingJobStatus.COMPLETED,
            now=self._clock(),
        )
        try:
            self._jobs.update(completed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.error(
                "event=catalog_enrichment.completion_consistency_risk job_id=%s enrichment_id=%s",
                job.job_id,
                stored.enrichment_id,
            )
            raise
        logger.info(
            "event=catalog_enrichment.completed job_id=%s enrichment_id=%s attempt_count=%s "
            "bullet_count=%s keyword_count=%s warning_count=%s",
            job.job_id,
            stored.enrichment_id,
            stored.generation_attempt_count,
            len(stored.feature_bullets),
            len(stored.search_keywords),
            len(stored.warning_codes),
        )
        return stored

    def _validate_setup(
        self, job: ProcessingJob
    ) -> tuple[CommerceCatalogProjection, CatalogEnrichmentPreparation]:
        try:
            product = self._products.get_by_id(job.product_id)
            if product is None:
                raise CatalogEnrichmentProductRequiredError()
            assert job.projection_id is not None
            projection = self._projections.get_by_id(job.projection_id)
            if projection is None:
                raise CatalogEnrichmentProjectionRequiredError()
            if projection.product_id != product.product_id:
                raise CatalogEnrichmentCrossProductProjectionError()
            if projection.status is CatalogProjectionStatus.BLOCKED:
                raise CatalogEnrichmentProjectionBlockedError()
            if (
                projection.status
                not in {CatalogProjectionStatus.READY, CatalogProjectionStatus.READY_WITH_WARNINGS}
                or projection.attribute_count != len(projection.attributes)
                or len(projection.schema_fingerprint) != 64
            ):
                raise CatalogEnrichmentLineageInvalidError()
            preparation = self._engine.prepare(projection)
            if any(
                result.prompt_version == preparation.prompt.prompt_version
                and result.provider == self._engine.provider
                and result.model == self._engine.model
                for result in self._results.get_by_projection_id(projection.projection_id)
            ):
                raise CatalogEnrichmentAlreadyExistsError()
            return projection, preparation
        except CatalogEnrichmentError:
            raise
        except CatalogEnrichmentRepositoryError as exc:
            raise CatalogEnrichmentStorageError() from exc
        except (ProductRepositoryError, CatalogProjectionRepositoryError) as exc:
            raise CatalogEnrichmentLineageInvalidError() from exc

    def _fail(self, running: ProcessingJob, error: CatalogEnrichmentError) -> None:
        logger.warning(
            "event=catalog_enrichment.failed job_id=%s error_code=%s",
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
                "event=catalog_enrichment.completion_consistency_risk job_id=%s",
                running.job_id,
            )
