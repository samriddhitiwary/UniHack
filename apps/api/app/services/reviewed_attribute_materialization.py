"""Product-level final reviewed attribute materialization orchestration."""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import (
    AttributeNormalizationRepositoryError,
    AttributeSelectionRepositoryError,
    AttributeValidationRepositoryError,
    CategoryAttributeSchemaRepositoryError,
    InvalidReviewedAttributeMaterializationJobError,
    ProcessingJobRepositoryError,
    ProductRepositoryError,
    ProductReviewRepositoryError,
    ReviewedAttributeMaterializationError,
    ReviewedAttributeRepositoryError,
    ReviewedMaterializationAlreadyExistsError,
    ReviewedMaterializationCrossProductLineageError,
    ReviewedMaterializationLineageMismatchError,
    ReviewedMaterializationResultStorageError,
    ReviewedMaterializationReviewNotCompletedError,
    ReviewedMaterializationReviewRequiredError,
    ReviewedMaterializationSchemaNotAvailableError,
)
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.domain.product_review import AttributeReviewDecision, ProductReviewSessionStatus
from app.domain.reviewed_attributes import FinalReviewedAttributeSet
from app.repositories.attribute_normalization import AttributeNormalizationResultRepository
from app.repositories.attribute_selection import AttributeSelectionResultRepository
from app.repositories.attribute_validation import AttributeValidationResultRepository
from app.repositories.category_schemas import CategoryAttributeSchemaRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_review import ProductReviewRepository
from app.repositories.products import ProductRepository
from app.repositories.reviewed_attributes import FinalReviewedAttributeRepository
from app.services.review_decision_resolver import ReviewDecisionResolver
from app.services.reviewed_attribute_materialization_engine import (
    ReviewedAttributeMaterializationEngine,
)

logger = logging.getLogger(__name__)


class ReviewedAttributeMaterializationService:
    def __init__(
        self,
        *,
        job_repository: ProcessingJobRepository,
        product_repository: ProductRepository,
        review_repository: ProductReviewRepository,
        selection_repository: AttributeSelectionResultRepository,
        validation_repository: AttributeValidationResultRepository,
        normalization_repository: AttributeNormalizationResultRepository,
        schema_repository: CategoryAttributeSchemaRepository,
        result_repository: FinalReviewedAttributeRepository,
        resolver: ReviewDecisionResolver,
        engine: ReviewedAttributeMaterializationEngine,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._jobs, self._products, self._reviews = (
            job_repository,
            product_repository,
            review_repository,
        )
        self._selections, self._validations, self._normalizations = (
            selection_repository,
            validation_repository,
            normalization_repository,
        )
        self._schemas, self._results, self._resolver, self._engine = (
            schema_repository,
            result_repository,
            resolver,
            engine,
        )
        self._clock = clock or (lambda: datetime.now(UTC))

    def materialize_for_job(self, *, job_id: UUID) -> FinalReviewedAttributeSet:
        job = self._jobs.get_by_id(job_id)
        if (
            job is None
            or job.job_type is not ProcessingJobType.REVIEWED_ATTRIBUTE_MATERIALIZATION
            or job.status is not ProcessingJobStatus.PENDING
            or job.source_id is not None
            or job.review_id is None
        ):
            raise InvalidReviewedAttributeMaterializationJobError()
        try:
            if self._products.get_by_id(job.product_id) is None:
                raise ReviewedMaterializationCrossProductLineageError()
            review = self._reviews.get_by_id(job.review_id)
            if review is None:
                raise ReviewedMaterializationReviewRequiredError()
            if review.product_id != job.product_id:
                raise ReviewedMaterializationCrossProductLineageError()
            if review.status is not ProductReviewSessionStatus.COMPLETED:
                raise ReviewedMaterializationReviewNotCompletedError()
            selection = self._selections.get_by_id(review.selection_id)
            validation = self._validations.get_by_id(review.validation_id)
            normalization = self._normalizations.get_by_id(review.normalization_id)
            schema = self._schemas.get_by_category_and_version(
                review.category, review.schema_version
            )
            if selection is None or validation is None or normalization is None:
                raise ReviewedMaterializationLineageMismatchError()
            if schema is None:
                raise ReviewedMaterializationSchemaNotAvailableError()
            if self._results.get_by_review_id(review.review_id) is not None:
                raise ReviewedMaterializationAlreadyExistsError()
            current = self._reviews.list_current_decisions(review.review_id)
            history: list[AttributeReviewDecision] = []
            cursor: str | None = None
            while True:
                page = self._reviews.list_decisions(review.review_id, limit=100, cursor=cursor)
                history.extend(page.items)
                cursor = page.next_cursor
                if cursor is None:
                    break
            decisions = tuple(
                self._resolver.resolve(
                    review_id=review.review_id,
                    product_id=review.product_id,
                    current=current,
                    history=history,
                ).values()
            )
        except ReviewedAttributeMaterializationError:
            raise
        except (
            ProductRepositoryError,
            ProductReviewRepositoryError,
            AttributeSelectionRepositoryError,
            AttributeValidationRepositoryError,
            AttributeNormalizationRepositoryError,
            CategoryAttributeSchemaRepositoryError,
            ReviewedAttributeRepositoryError,
        ) as exc:
            raise ReviewedMaterializationLineageMismatchError() from exc
        running = self._jobs.update(
            transition_processing_job(job, ProcessingJobStatus.RUNNING, now=self._clock()),
            expected_version=job.version,
        )
        logger.info(
            "event=reviewed_attribute_materialization.started job_id=%s product_id=%s review_id=%s",
            job.job_id,
            job.product_id,
            review.review_id,
        )
        try:
            result = self._engine.materialize(
                job_id=job.job_id,
                review=review,
                current_decisions=decisions,
                schema=schema,
                selection_result=selection,
                validation_result=validation,
                normalization_result=normalization,
                now=self._clock(),
            )
            stored = self._results.create(result)
        except ReviewedAttributeMaterializationError as exc:
            self._fail(running, exc)
            raise
        except ReviewedAttributeRepositoryError as exc:
            storage_error = ReviewedMaterializationResultStorageError()
            self._fail(running, storage_error)
            raise storage_error from exc
        except Exception as exc:
            generic_error = ReviewedAttributeMaterializationError()
            self._fail(running, generic_error)
            raise generic_error from exc
        completed = transition_processing_job(
            replace(
                running, result_reference=f"reviewed-attribute-results/{stored.materialization_id}"
            ),
            ProcessingJobStatus.COMPLETED,
            now=self._clock(),
        )
        try:
            self._jobs.update(completed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.error(
                "event=reviewed_attribute_materialization.completion_consistency_risk "
                "job_id=%s materialization_id=%s",
                job.job_id,
                stored.materialization_id,
            )
            raise
        logger.info(
            "event=reviewed_attribute_materialization.completed job_id=%s "
            "materialization_id=%s attribute_count=%s",
            job.job_id,
            stored.materialization_id,
            stored.attribute_count,
        )
        return stored

    def _fail(self, running: ProcessingJob, error: ReviewedAttributeMaterializationError) -> None:
        failed = transition_processing_job(
            replace(running, error_code=error.code, error_message=error.safe_message),
            ProcessingJobStatus.FAILED,
            now=self._clock(),
        )
        try:
            self._jobs.update(failed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.exception(
                "event=reviewed_attribute_materialization.completion_consistency_risk job_id=%s",
                running.job_id,
            )
