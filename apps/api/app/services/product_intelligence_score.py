"""Product-level Product Intelligence Score orchestration."""

import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.exceptions import (
    InvalidProductIntelligenceScoreJobError,
    ProcessingJobRepositoryError,
    ProductIntelligenceAlreadyExistsError,
    ProductIntelligenceCrossProductLineageError,
    ProductIntelligenceEnrichmentMismatchError,
    ProductIntelligenceLimitExceededError,
    ProductIntelligenceLineageMismatchError,
    ProductIntelligenceProjectionRequiredError,
    ProductIntelligenceScoreError,
    ProductIntelligenceScoreRepositoryError,
    ProductIntelligenceStorageError,
)
from app.domain.attribute_completeness import AttributeCompletenessResult
from app.domain.attribute_conflicts import AttributeConflictDetectionResult
from app.domain.attribute_selection import AttributeSelectionResult
from app.domain.attribute_validation import AttributeValidationResult
from app.domain.catalog_enrichment import CatalogEnrichmentResult
from app.domain.catalog_projection import CommerceCatalogProjection
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.domain.product_intelligence import ProductIntelligenceScoreResult
from app.domain.product_review import ProductReviewSession, ProductReviewSessionStatus
from app.domain.reviewed_attributes import FinalReviewedAttributeSet
from app.repositories.attribute_completeness import AttributeCompletenessResultRepository
from app.repositories.attribute_conflicts import AttributeConflictDetectionResultRepository
from app.repositories.attribute_selection import AttributeSelectionResultRepository
from app.repositories.attribute_validation import AttributeValidationResultRepository
from app.repositories.catalog_enrichment import CatalogEnrichmentResultRepository
from app.repositories.catalog_projection import CommerceCatalogProjectionRepository
from app.repositories.dynamodb_product_intelligence import product_intelligence_input_key
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_intelligence import ProductIntelligenceScoreRepository
from app.repositories.product_review import ProductReviewRepository
from app.repositories.products import ProductRepository
from app.repositories.reviewed_attributes import FinalReviewedAttributeRepository
from app.services.product_intelligence_engine import ProductIntelligenceEngine
from app.services.product_intelligence_policy import POLICY_VERSION

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _ScoreInputs:
    projection: CommerceCatalogProjection
    completeness: AttributeCompletenessResult
    validation: AttributeValidationResult
    conflicts: AttributeConflictDetectionResult
    selection: AttributeSelectionResult
    review: ProductReviewSession
    materialization: FinalReviewedAttributeSet
    enrichment: CatalogEnrichmentResult | None


class ProductIntelligenceScoreService:
    def __init__(
        self,
        *,
        job_repository: ProcessingJobRepository,
        product_repository: ProductRepository,
        projection_repository: CommerceCatalogProjectionRepository,
        completeness_repository: AttributeCompletenessResultRepository,
        validation_repository: AttributeValidationResultRepository,
        conflict_repository: AttributeConflictDetectionResultRepository,
        selection_repository: AttributeSelectionResultRepository,
        review_repository: ProductReviewRepository,
        materialization_repository: FinalReviewedAttributeRepository,
        enrichment_repository: CatalogEnrichmentResultRepository,
        result_repository: ProductIntelligenceScoreRepository,
        engine: ProductIntelligenceEngine,
        max_attributes: int = 100,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self._jobs, self._products, self._projections = (
            job_repository,
            product_repository,
            projection_repository,
        )
        self._completeness, self._validation = completeness_repository, validation_repository
        self._conflicts, self._selections = conflict_repository, selection_repository
        self._reviews, self._materializations = review_repository, materialization_repository
        self._enrichments, self._results, self._engine = (
            enrichment_repository,
            result_repository,
            engine,
        )
        self._max_attributes = max_attributes
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid = uuid_factory or uuid4

    def score_for_job(self, *, job_id: UUID) -> ProductIntelligenceScoreResult:
        job = self._jobs.get_by_id(job_id)
        if (
            job is None
            or job.job_type is not ProcessingJobType.PRODUCT_INTELLIGENCE_SCORE
            or job.status is not ProcessingJobStatus.PENDING
            or job.source_id is not None
            or job.projection_id is None
        ):
            raise InvalidProductIntelligenceScoreJobError()
        inputs = self._validate_setup(job)
        running = self._jobs.update(
            transition_processing_job(job, ProcessingJobStatus.RUNNING, now=self._clock()),
            expected_version=job.version,
        )
        score_id = self._uuid()
        logger.info(
            "event=product_intelligence_score.started job_id=%s product_id=%s "
            "projection_id=%s enrichment_id=%s score_id=%s policy_version=%s",
            job.job_id,
            job.product_id,
            job.projection_id,
            job.enrichment_id,
            score_id,
            POLICY_VERSION,
        )
        try:
            result = self._engine.evaluate(
                score_id=score_id,
                job_id=job.job_id,
                created_at=self._clock().astimezone(UTC),
                projection=inputs.projection,
                completeness=inputs.completeness,
                validation=inputs.validation,
                conflicts=inputs.conflicts,
                selection=inputs.selection,
                review=inputs.review,
                materialization=inputs.materialization,
                enrichment=inputs.enrichment,
            )
            stored = self._results.create(result)
        except ProductIntelligenceScoreRepositoryError as exc:
            error: ProductIntelligenceScoreError = ProductIntelligenceStorageError()
            self._fail(running, error)
            raise error from exc
        except ProductIntelligenceScoreError as exc:
            self._fail(running, exc)
            raise
        except Exception as exc:
            error = ProductIntelligenceScoreError()
            self._fail(running, error)
            raise error from exc
        completed = transition_processing_job(
            replace(
                running, result_reference=f"product-intelligence-score-results/{stored.score_id}"
            ),
            ProcessingJobStatus.COMPLETED,
            now=self._clock(),
        )
        try:
            self._jobs.update(completed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.error(
                "event=product_intelligence_score.completion_consistency_risk "
                "job_id=%s score_id=%s",
                job.job_id,
                stored.score_id,
            )
            raise
        logger.info(
            "event=product_intelligence_score.completed job_id=%s score_id=%s "
            "overall_score_bp=%s grade=%s component_count=%s improvement_count=%s",
            job.job_id,
            stored.score_id,
            stored.overall_score_bp,
            stored.grade,
            len(stored.components),
            len(stored.improvement_codes),
        )
        return stored

    def _validate_setup(self, job: ProcessingJob) -> _ScoreInputs:
        try:
            product = self._products.get_by_id(job.product_id)
            if product is None:
                raise ProductIntelligenceLineageMismatchError()
            assert job.projection_id is not None
            projection = self._projections.get_by_id(job.projection_id)
            if projection is None:
                raise ProductIntelligenceProjectionRequiredError()
            if projection.product_id != job.product_id:
                raise ProductIntelligenceCrossProductLineageError()
            materialization = self._materializations.get_by_id(projection.materialization_id)
            review = self._reviews.get_by_id(projection.review_id)
            selection = self._selections.get_by_id(projection.selection_id)
            validation = self._validation.get_by_id(projection.validation_id)
            completeness = self._completeness.get_by_id(projection.completeness_id)
            conflicts = self._conflicts.get_by_id(projection.conflict_detection_id)
            if any(
                item is None
                for item in (
                    materialization,
                    review,
                    selection,
                    validation,
                    completeness,
                    conflicts,
                )
            ):
                raise ProductIntelligenceLineageMismatchError()
            assert isinstance(materialization, FinalReviewedAttributeSet)
            assert isinstance(review, ProductReviewSession)
            assert isinstance(selection, AttributeSelectionResult)
            assert isinstance(validation, AttributeValidationResult)
            assert isinstance(completeness, AttributeCompletenessResult)
            assert isinstance(conflicts, AttributeConflictDetectionResult)
            if (
                review.status is not ProductReviewSessionStatus.COMPLETED
                or max(
                    len(item.attributes)
                    for item in (projection, materialization, selection, completeness, conflicts)
                )
                > self._max_attributes
            ):
                raise ProductIntelligenceLimitExceededError()
            self._engine._validate_lineage(
                projection, completeness, validation, conflicts, selection, review, materialization
            )
            enrichment = (
                self._enrichments.get_by_id(job.enrichment_id) if job.enrichment_id else None
            )
            if job.enrichment_id and enrichment is None:
                raise ProductIntelligenceEnrichmentMismatchError()
            if enrichment is not None and (
                enrichment.product_id != job.product_id
                or enrichment.projection_id != projection.projection_id
                or enrichment.schema_version != projection.schema_version
                or enrichment.schema_fingerprint != projection.schema_fingerprint
            ):
                raise ProductIntelligenceEnrichmentMismatchError()
            key = product_intelligence_input_key(
                projection.projection_id, job.enrichment_id, POLICY_VERSION
            )
            if self._results.get_by_input_key(key) is not None:
                raise ProductIntelligenceAlreadyExistsError()
            return _ScoreInputs(
                projection=projection,
                completeness=completeness,
                validation=validation,
                conflicts=conflicts,
                selection=selection,
                review=review,
                materialization=materialization,
                enrichment=enrichment,
            )
        except ProductIntelligenceScoreError:
            raise
        except ProductIntelligenceScoreRepositoryError as exc:
            raise ProductIntelligenceStorageError() from exc
        except Exception as exc:
            raise ProductIntelligenceLineageMismatchError() from exc

    def _fail(self, running: ProcessingJob, error: ProductIntelligenceScoreError) -> None:
        logger.warning(
            "event=product_intelligence_score.failed job_id=%s error_code=%s",
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
                "event=product_intelligence_score.completion_consistency_risk job_id=%s",
                running.job_id,
            )
