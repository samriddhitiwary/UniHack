"""Product-level attribute normalization job orchestration."""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import (
    AttributeNormalizationError,
    AttributeNormalizationExtractionRequiredError,
    AttributeNormalizationRepositoryError,
    AttributeNormalizationResultStorageError,
    AttributeNormalizationSchemaMismatchError,
    AttributeNormalizationSchemaNotAvailableError,
    CategoryAttributeSchemaRepositoryError,
    InvalidAttributeNormalizationJobError,
    ProcessingJobRepositoryError,
    ProductRepositoryError,
    StructuredAttributeExtractionRepositoryError,
)
from app.domain.attribute_normalization import AttributeNormalizationResult
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.repositories.attribute_normalization import AttributeNormalizationResultRepository
from app.repositories.category_schemas import CategoryAttributeSchemaRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.products import ProductRepository
from app.repositories.structured_attribute_extraction import (
    StructuredAttributeExtractionResultRepository,
)
from app.services.attribute_normalization_engine import AttributeNormalizationEngine

logger = logging.getLogger(__name__)


class AttributeNormalizationService:
    def __init__(
        self,
        *,
        job_repository: ProcessingJobRepository,
        product_repository: ProductRepository,
        extraction_repository: StructuredAttributeExtractionResultRepository,
        schema_repository: CategoryAttributeSchemaRepository,
        result_repository: AttributeNormalizationResultRepository,
        engine: AttributeNormalizationEngine,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._jobs, self._products = job_repository, product_repository
        self._extractions, self._schemas = extraction_repository, schema_repository
        self._results, self._engine = result_repository, engine
        self._clock = clock or (lambda: datetime.now(UTC))

    def normalize_for_job(self, *, job_id: UUID) -> AttributeNormalizationResult:
        job = self._jobs.get_by_id(job_id)
        if (
            job is None
            or job.job_type is not ProcessingJobType.ATTRIBUTE_NORMALIZATION
            or job.status is not ProcessingJobStatus.PENDING
            or job.source_id is not None
            or job.attribute_extraction_id is None
        ):
            raise InvalidAttributeNormalizationJobError()
        try:
            if self._products.get_by_id(job.product_id) is None:
                raise AttributeNormalizationExtractionRequiredError()
            extraction = self._extractions.get_by_id(job.attribute_extraction_id)
            if extraction is None or extraction.product_id != job.product_id:
                raise AttributeNormalizationExtractionRequiredError()
            schema = self._schemas.get_by_category_and_version(
                extraction.category, extraction.schema_version
            )
            if schema is None:
                raise AttributeNormalizationSchemaNotAvailableError()
            if schema.schema_fingerprint != extraction.schema_fingerprint:
                raise AttributeNormalizationSchemaMismatchError()
            if self._results.get_by_job_id(job.job_id) is not None:
                raise InvalidAttributeNormalizationJobError()
        except AttributeNormalizationError:
            raise
        except StructuredAttributeExtractionRepositoryError as exc:
            raise AttributeNormalizationExtractionRequiredError() from exc
        except CategoryAttributeSchemaRepositoryError as exc:
            raise AttributeNormalizationSchemaNotAvailableError() from exc
        except ProductRepositoryError as exc:
            raise AttributeNormalizationExtractionRequiredError() from exc
        except AttributeNormalizationRepositoryError as exc:
            raise AttributeNormalizationResultStorageError() from exc

        running = self._jobs.update(
            transition_processing_job(job, ProcessingJobStatus.RUNNING, now=self._clock()),
            expected_version=job.version,
        )
        logger.info(
            "event=attribute_normalization.started job_id=%s product_id=%s extraction_id=%s "
            "category=%s schema_version=%s",
            job.job_id,
            job.product_id,
            extraction.extraction_id,
            extraction.category.value,
            extraction.schema_version,
        )
        try:
            result = self._engine.normalize(
                job_id=job.job_id,
                extraction_result=extraction,
                schema=schema,
                now=self._clock(),
            )
            stored = self._results.create(result)
        except AttributeNormalizationError as exc:
            self._fail(running, exc)
            raise
        except AttributeNormalizationRepositoryError as exc:
            error = AttributeNormalizationResultStorageError()
            self._fail(running, error)
            raise error from exc
        except Exception as exc:
            unexpected_error = AttributeNormalizationError()
            self._fail(running, unexpected_error)
            raise unexpected_error from exc

        completed = replace(
            running,
            result_reference=f"attribute-normalization-results/{stored.normalization_id}",
        )
        completed = transition_processing_job(
            completed, ProcessingJobStatus.COMPLETED, now=self._clock()
        )
        try:
            self._jobs.update(completed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.error(
                "event=attribute_normalization.completion_consistency_risk job_id=%s "
                "product_id=%s normalization_id=%s",
                job.job_id,
                job.product_id,
                stored.normalization_id,
            )
            raise
        logger.info(
            "event=attribute_normalization.%s job_id=%s product_id=%s extraction_id=%s "
            "normalization_id=%s category=%s schema_version=%s candidate_count=%s "
            "converted_count=%s unsupported_unit_count=%s invalid_value_count=%s "
            "engine=%s engine_version=%s",
            stored.status.value.lower(),
            job.job_id,
            job.product_id,
            extraction.extraction_id,
            stored.normalization_id,
            stored.category.value,
            stored.schema_version,
            stored.candidate_count,
            stored.converted_count,
            stored.unsupported_unit_count,
            stored.invalid_value_count,
            stored.engine,
            stored.engine_version,
        )
        return stored

    def _fail(self, running: ProcessingJob, error: AttributeNormalizationError) -> None:
        failed = replace(running, error_code=error.code, error_message=error.safe_message)
        failed = transition_processing_job(failed, ProcessingJobStatus.FAILED, now=self._clock())
        try:
            self._jobs.update(failed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.exception(
                "event=attribute_normalization.completion_consistency_risk job_id=%s",
                running.job_id,
            )
