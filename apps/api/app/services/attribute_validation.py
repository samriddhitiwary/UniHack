"""Product-level attribute validation job orchestration."""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import (
    AttributeNormalizationRepositoryError,
    AttributeValidationCrossProductLineageError,
    AttributeValidationError,
    AttributeValidationNormalizationRequiredError,
    AttributeValidationRepositoryError,
    AttributeValidationResultStorageError,
    AttributeValidationSchemaMismatchError,
    AttributeValidationSchemaNotAvailableError,
    CategoryAttributeSchemaRepositoryError,
    InvalidAttributeValidationJobError,
    ProcessingJobRepositoryError,
    ProductRepositoryError,
)
from app.domain.attribute_validation import AttributeValidationResult
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.repositories.attribute_normalization import AttributeNormalizationResultRepository
from app.repositories.attribute_validation import AttributeValidationResultRepository
from app.repositories.category_schemas import CategoryAttributeSchemaRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.products import ProductRepository
from app.services.attribute_validation_engine import AttributeValidationEngine

logger = logging.getLogger(__name__)


class AttributeValidationService:
    def __init__(
        self,
        *,
        job_repository: ProcessingJobRepository,
        product_repository: ProductRepository,
        normalization_repository: AttributeNormalizationResultRepository,
        schema_repository: CategoryAttributeSchemaRepository,
        result_repository: AttributeValidationResultRepository,
        engine: AttributeValidationEngine,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._jobs, self._products = job_repository, product_repository
        self._normalizations, self._schemas = normalization_repository, schema_repository
        self._results, self._engine = result_repository, engine
        self._clock = clock or (lambda: datetime.now(UTC))

    def validate_for_job(self, *, job_id: UUID) -> AttributeValidationResult:
        job = self._jobs.get_by_id(job_id)
        if (
            job is None
            or job.job_type is not ProcessingJobType.ATTRIBUTE_VALIDATION
            or job.status is not ProcessingJobStatus.PENDING
            or job.source_id is not None
            or job.attribute_normalization_id is None
        ):
            raise InvalidAttributeValidationJobError()
        try:
            if self._products.get_by_id(job.product_id) is None:
                raise AttributeValidationNormalizationRequiredError()
            normalization = self._normalizations.get_by_id(job.attribute_normalization_id)
            if normalization is None:
                raise AttributeValidationNormalizationRequiredError()
            if normalization.product_id != job.product_id:
                raise AttributeValidationCrossProductLineageError()
            schema = self._schemas.get_by_category_and_version(
                normalization.category, normalization.schema_version
            )
            if schema is None:
                raise AttributeValidationSchemaNotAvailableError()
            if schema.schema_fingerprint != normalization.schema_fingerprint:
                raise AttributeValidationSchemaMismatchError()
            if self._results.get_by_job_id(job.job_id) is not None:
                raise InvalidAttributeValidationJobError()
        except AttributeValidationError:
            raise
        except (ProductRepositoryError, AttributeNormalizationRepositoryError) as exc:
            raise AttributeValidationNormalizationRequiredError() from exc
        except CategoryAttributeSchemaRepositoryError as exc:
            raise AttributeValidationSchemaNotAvailableError() from exc
        except AttributeValidationRepositoryError as exc:
            raise AttributeValidationResultStorageError() from exc
        running = self._jobs.update(
            transition_processing_job(job, ProcessingJobStatus.RUNNING, now=self._clock()),
            expected_version=job.version,
        )
        logger.info(
            "event=attribute_validation.started job_id=%s product_id=%s normalization_id=%s",
            job.job_id,
            job.product_id,
            normalization.normalization_id,
        )
        try:
            stored = self._results.create(
                self._engine.validate(
                    job_id=job.job_id,
                    normalization_result=normalization,
                    schema=schema,
                    now=self._clock(),
                )
            )
        except AttributeValidationError as exc:
            self._fail(running, exc)
            raise
        except AttributeValidationRepositoryError as exc:
            storage_error = AttributeValidationResultStorageError()
            self._fail(running, storage_error)
            raise storage_error from exc
        except Exception as exc:
            unexpected_error = AttributeValidationError()
            self._fail(running, unexpected_error)
            raise unexpected_error from exc
        completed = transition_processing_job(
            replace(
                running, result_reference=f"attribute-validation-results/{stored.validation_id}"
            ),
            ProcessingJobStatus.COMPLETED,
            now=self._clock(),
        )
        try:
            self._jobs.update(completed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.error(
                "event=attribute_validation.completion_consistency_risk job_id=%s validation_id=%s",
                job.job_id,
                stored.validation_id,
            )
            raise
        event = (
            "attribute_validation.completed_with_issues"
            if stored.issue_count
            else "attribute_validation.completed"
        )
        logger.info(
            "event=%s job_id=%s validation_id=%s valid_count=%s invalid_count=%s",
            event,
            job.job_id,
            stored.validation_id,
            stored.valid_count,
            stored.invalid_count,
        )
        return stored

    def _fail(self, running: ProcessingJob, error: AttributeValidationError) -> None:
        failed = transition_processing_job(
            replace(running, error_code=error.code, error_message=error.safe_message),
            ProcessingJobStatus.FAILED,
            now=self._clock(),
        )
        try:
            self._jobs.update(failed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.exception(
                "event=attribute_validation.completion_consistency_risk job_id=%s", running.job_id
            )
