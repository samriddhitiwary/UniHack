"""Product-level attribute completeness job orchestration."""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import (
    AttributeCompletenessConflictResultRequiredError,
    AttributeCompletenessCrossProductLineageError,
    AttributeCompletenessError,
    AttributeCompletenessRepositoryError,
    AttributeCompletenessResultStorageError,
    AttributeCompletenessSchemaMismatchError,
    AttributeCompletenessSchemaNotAvailableError,
    AttributeConflictRepositoryError,
    CategoryAttributeSchemaRepositoryError,
    InvalidAttributeCompletenessJobError,
    ProcessingJobRepositoryError,
    ProductRepositoryError,
)
from app.domain.attribute_completeness import AttributeCompletenessResult
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.repositories.attribute_completeness import AttributeCompletenessResultRepository
from app.repositories.attribute_conflicts import AttributeConflictDetectionResultRepository
from app.repositories.category_schemas import CategoryAttributeSchemaRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.products import ProductRepository
from app.services.attribute_completeness_engine import AttributeCompletenessEngine

logger = logging.getLogger(__name__)


class AttributeCompletenessService:
    def __init__(
        self,
        *,
        job_repository: ProcessingJobRepository,
        product_repository: ProductRepository,
        conflict_repository: AttributeConflictDetectionResultRepository,
        schema_repository: CategoryAttributeSchemaRepository,
        result_repository: AttributeCompletenessResultRepository,
        engine: AttributeCompletenessEngine,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._jobs, self._products = job_repository, product_repository
        self._conflicts, self._schemas = conflict_repository, schema_repository
        self._results, self._engine = result_repository, engine
        self._clock = clock or (lambda: datetime.now(UTC))

    def evaluate_for_job(self, *, job_id: UUID) -> AttributeCompletenessResult:
        job = self._jobs.get_by_id(job_id)
        if (
            job is None
            or job.job_type is not ProcessingJobType.ATTRIBUTE_COMPLETENESS
            or job.status is not ProcessingJobStatus.PENDING
            or job.source_id is not None
            or job.attribute_conflict_detection_id is None
        ):
            raise InvalidAttributeCompletenessJobError()
        try:
            if self._products.get_by_id(job.product_id) is None:
                raise AttributeCompletenessConflictResultRequiredError()
            conflict = self._conflicts.get_by_id(job.attribute_conflict_detection_id)
            if conflict is None:
                raise AttributeCompletenessConflictResultRequiredError()
            if conflict.product_id != job.product_id:
                raise AttributeCompletenessCrossProductLineageError()
            schema = self._schemas.get_by_category_and_version(
                conflict.category, conflict.schema_version
            )
            if schema is None:
                raise AttributeCompletenessSchemaNotAvailableError()
            if schema.schema_fingerprint != conflict.schema_fingerprint:
                raise AttributeCompletenessSchemaMismatchError()
            if self._results.get_by_job_id(job.job_id) is not None:
                raise InvalidAttributeCompletenessJobError()
        except AttributeCompletenessError:
            raise
        except (ProductRepositoryError, AttributeConflictRepositoryError) as exc:
            raise AttributeCompletenessConflictResultRequiredError() from exc
        except CategoryAttributeSchemaRepositoryError as exc:
            raise AttributeCompletenessSchemaNotAvailableError() from exc
        except AttributeCompletenessRepositoryError as exc:
            raise AttributeCompletenessResultStorageError() from exc
        running = self._jobs.update(
            transition_processing_job(job, ProcessingJobStatus.RUNNING, now=self._clock()),
            expected_version=job.version,
        )
        logger.info(
            "event=attribute_completeness.started job_id=%s product_id=%s conflict_detection_id=%s",
            job.job_id,
            job.product_id,
            conflict.conflict_detection_id,
        )
        try:
            stored = self._results.create(
                self._engine.evaluate(
                    job_id=job.job_id, conflict_result=conflict, schema=schema, now=self._clock()
                )
            )
        except AttributeCompletenessError as exc:
            self._fail(running, exc)
            raise
        except AttributeCompletenessRepositoryError as exc:
            error = AttributeCompletenessResultStorageError()
            self._fail(running, error)
            raise error from exc
        except Exception as exc:
            unexpected_error = AttributeCompletenessError()
            self._fail(running, unexpected_error)
            raise unexpected_error from exc
        completed = transition_processing_job(
            replace(
                running, result_reference=f"attribute-completeness-results/{stored.completeness_id}"
            ),
            ProcessingJobStatus.COMPLETED,
            now=self._clock(),
        )
        try:
            self._jobs.update(completed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.error(
                "event=attribute_completeness.completion_consistency_risk "
                "job_id=%s completeness_id=%s",
                job.job_id,
                stored.completeness_id,
            )
            raise
        logger.info(
            "event=attribute_completeness.completed job_id=%s status=%s required_resolved_bp=%s",
            job.job_id,
            stored.status.value,
            stored.required_resolved_bp,
        )
        return stored

    def _fail(self, running: ProcessingJob, error: AttributeCompletenessError) -> None:
        failed = transition_processing_job(
            replace(running, error_code=error.code, error_message=error.safe_message),
            ProcessingJobStatus.FAILED,
            now=self._clock(),
        )
        try:
            self._jobs.update(failed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.exception(
                "event=attribute_completeness.completion_consistency_risk job_id=%s", running.job_id
            )
