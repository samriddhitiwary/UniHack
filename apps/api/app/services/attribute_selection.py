"""Product-level attribute selection job orchestration."""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import (
    AttributeCompletenessRepositoryError,
    AttributeConflictRepositoryError,
    AttributeNormalizationRepositoryError,
    AttributeSelectionCompletenessResultRequiredError,
    AttributeSelectionConflictResultRequiredError,
    AttributeSelectionCrossProductLineageError,
    AttributeSelectionError,
    AttributeSelectionLineageMismatchError,
    AttributeSelectionNormalizationRequiredError,
    AttributeSelectionRepositoryError,
    AttributeSelectionResultStorageError,
    AttributeSelectionValidationResultRequiredError,
    AttributeValidationRepositoryError,
    InvalidAttributeSelectionJobError,
    ProcessingJobRepositoryError,
    ProductRepositoryError,
)
from app.domain.attribute_selection import AttributeSelectionResult
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.repositories.attribute_completeness import AttributeCompletenessResultRepository
from app.repositories.attribute_conflicts import AttributeConflictDetectionResultRepository
from app.repositories.attribute_normalization import AttributeNormalizationResultRepository
from app.repositories.attribute_selection import AttributeSelectionResultRepository
from app.repositories.attribute_validation import AttributeValidationResultRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.products import ProductRepository
from app.services.attribute_selection_engine import AttributeSelectionEngine

logger = logging.getLogger(__name__)


class AttributeSelectionService:
    def __init__(
        self,
        *,
        job_repository: ProcessingJobRepository,
        product_repository: ProductRepository,
        conflict_repository: AttributeConflictDetectionResultRepository,
        validation_repository: AttributeValidationResultRepository,
        completeness_repository: AttributeCompletenessResultRepository,
        normalization_repository: AttributeNormalizationResultRepository,
        result_repository: AttributeSelectionResultRepository,
        engine: AttributeSelectionEngine,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._jobs, self._products, self._conflicts = (
            job_repository,
            product_repository,
            conflict_repository,
        )
        self._validations, self._completeness = validation_repository, completeness_repository
        self._normalizations, self._results, self._engine = (
            normalization_repository,
            result_repository,
            engine,
        )
        self._clock = clock or (lambda: datetime.now(UTC))

    def select_for_job(self, *, job_id: UUID) -> AttributeSelectionResult:
        job = self._jobs.get_by_id(job_id)
        if (
            job is None
            or job.job_type is not ProcessingJobType.ATTRIBUTE_SELECTION
            or job.status is not ProcessingJobStatus.PENDING
            or job.source_id is not None
            or job.attribute_conflict_detection_id is None
            or job.attribute_validation_id is None
            or job.attribute_completeness_id is None
            or job.attribute_normalization_id is None
        ):
            raise InvalidAttributeSelectionJobError()
        try:
            if self._products.get_by_id(job.product_id) is None:
                raise AttributeSelectionCrossProductLineageError()
            conflict = self._conflicts.get_by_id(job.attribute_conflict_detection_id)
            if conflict is None:
                raise AttributeSelectionConflictResultRequiredError()
            validation = self._validations.get_by_id(job.attribute_validation_id)
            if validation is None:
                raise AttributeSelectionValidationResultRequiredError()
            completeness = self._completeness.get_by_id(job.attribute_completeness_id)
            if completeness is None:
                raise AttributeSelectionCompletenessResultRequiredError()
            normalization = self._normalizations.get_by_id(job.attribute_normalization_id)
            if normalization is None:
                raise AttributeSelectionNormalizationRequiredError()
            if (
                len(
                    {
                        conflict.product_id,
                        validation.product_id,
                        completeness.product_id,
                        normalization.product_id,
                        job.product_id,
                    }
                )
                != 1
            ):
                raise AttributeSelectionCrossProductLineageError()
            lineage = {
                (
                    value.normalization_id,
                    value.extraction_id,
                    value.classification_id,
                    value.category,
                    value.schema_version,
                    value.schema_fingerprint,
                )
                for value in (conflict, validation, completeness, normalization)
            }
            if (
                len(lineage) != 1
                or completeness.conflict_detection_id != conflict.conflict_detection_id
            ):
                raise AttributeSelectionLineageMismatchError()
            if self._results.get_by_job_id(job.job_id) is not None:
                raise InvalidAttributeSelectionJobError()
        except AttributeSelectionError:
            raise
        except (
            ProductRepositoryError,
            AttributeConflictRepositoryError,
            AttributeValidationRepositoryError,
            AttributeCompletenessRepositoryError,
            AttributeNormalizationRepositoryError,
            AttributeSelectionRepositoryError,
        ) as exc:
            raise AttributeSelectionLineageMismatchError() from exc
        running = self._jobs.update(
            transition_processing_job(job, ProcessingJobStatus.RUNNING, now=self._clock()),
            expected_version=job.version,
        )
        logger.info(
            "event=attribute_selection.started job_id=%s product_id=%s", job.job_id, job.product_id
        )
        try:
            stored = self._results.create(
                self._engine.select(
                    job_id=job.job_id,
                    conflict_result=conflict,
                    validation_result=validation,
                    completeness_result=completeness,
                    normalization_result=normalization,
                    now=self._clock(),
                )
            )
        except AttributeSelectionError as exc:
            self._fail(running, exc)
            raise
        except AttributeSelectionRepositoryError as exc:
            storage_error = AttributeSelectionResultStorageError()
            self._fail(running, storage_error)
            raise storage_error from exc
        except Exception as exc:
            error = AttributeSelectionError()
            self._fail(running, error)
            raise error from exc
        completed = transition_processing_job(
            replace(running, result_reference=f"attribute-selection-results/{stored.selection_id}"),
            ProcessingJobStatus.COMPLETED,
            now=self._clock(),
        )
        try:
            self._jobs.update(completed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.error(
                "event=attribute_selection.completion_consistency_risk job_id=%s selection_id=%s",
                job.job_id,
                stored.selection_id,
            )
            raise
        logger.info(
            "event=attribute_selection.completed job_id=%s overall_status=%s "
            "required_review_count=%s",
            job.job_id,
            stored.overall_status.value,
            stored.required_review_required_count,
        )
        return stored

    def _fail(self, running: ProcessingJob, error: AttributeSelectionError) -> None:
        failed = transition_processing_job(
            replace(running, error_code=error.code, error_message=error.safe_message),
            ProcessingJobStatus.FAILED,
            now=self._clock(),
        )
        try:
            self._jobs.update(failed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.exception(
                "event=attribute_selection.completion_consistency_risk job_id=%s", running.job_id
            )
