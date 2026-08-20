"""Pure deterministic Product Intelligence Score evaluation engine."""

from datetime import datetime
from uuid import UUID

from app.core.exceptions import (
    ProductIntelligenceEnrichmentMismatchError,
    ProductIntelligenceLineageMismatchError,
)
from app.domain.attribute_completeness import AttributeCompletenessResult
from app.domain.attribute_conflicts import AttributeConflictDetectionResult
from app.domain.attribute_selection import AttributeSelectionResult
from app.domain.attribute_validation import AttributeValidationResult
from app.domain.catalog_enrichment import CatalogEnrichmentResult
from app.domain.catalog_projection import CommerceCatalogProjection
from app.domain.product_intelligence import (
    ProductIntelligenceMetric,
    ProductIntelligenceScoreResult,
)
from app.domain.product_review import ProductReviewSession, ProductReviewSessionStatus
from app.domain.reviewed_attributes import FinalReviewedAttributeSet
from app.services.product_intelligence_ai_scorer import ProductIntelligenceAiScorer
from app.services.product_intelligence_completeness_scorer import (
    ProductIntelligenceCompletenessScorer,
)
from app.services.product_intelligence_conflict_scorer import ProductIntelligenceConflictScorer
from app.services.product_intelligence_corroboration_scorer import (
    ProductIntelligenceCorroborationScorer,
)
from app.services.product_intelligence_explanation import ProductIntelligenceExplanationBuilder
from app.services.product_intelligence_policy import POLICY_VERSION
from app.services.product_intelligence_review_scorer import ProductIntelligenceReviewScorer
from app.services.product_intelligence_score_calculator import ProductIntelligenceScoreCalculator
from app.services.product_intelligence_validation_scorer import ProductIntelligenceValidationScorer


class ProductIntelligenceEngine:
    def __init__(self) -> None:
        self._completeness = ProductIntelligenceCompletenessScorer()
        self._validation = ProductIntelligenceValidationScorer()
        self._corroboration = ProductIntelligenceCorroborationScorer()
        self._conflict = ProductIntelligenceConflictScorer()
        self._review = ProductIntelligenceReviewScorer()
        self._ai = ProductIntelligenceAiScorer()
        self._calculator = ProductIntelligenceScoreCalculator()
        self._explanation = ProductIntelligenceExplanationBuilder()

    def evaluate(
        self,
        *,
        score_id: UUID,
        job_id: UUID,
        projection: CommerceCatalogProjection,
        completeness: AttributeCompletenessResult,
        validation: AttributeValidationResult,
        conflicts: AttributeConflictDetectionResult,
        selection: AttributeSelectionResult,
        review: ProductReviewSession,
        materialization: FinalReviewedAttributeSet,
        enrichment: CatalogEnrichmentResult | None,
        created_at: datetime,
    ) -> ProductIntelligenceScoreResult:
        self._validate_lineage(
            projection, completeness, validation, conflicts, selection, review, materialization
        )
        if enrichment is not None and (
            enrichment.product_id != projection.product_id
            or enrichment.projection_id != projection.projection_id
            or enrichment.schema_version != projection.schema_version
            or enrichment.schema_fingerprint != projection.schema_fingerprint
        ):
            raise ProductIntelligenceEnrichmentMismatchError()
        raw = (
            self._completeness.score(completeness),
            self._validation.score(materialization, validation),
            self._corroboration.score(materialization, selection),
            self._conflict.score(materialization, conflicts),
            self._review.score(materialization),
            self._ai.score(enrichment),
        )
        components, overall, grade = self._calculator.calculate(raw)
        strengths, improvements, top = self._explanation.build(components)
        metrics = tuple(
            ProductIntelligenceMetric(
                name=f"{item.component.value}.{metric.name}", value=metric.value
            )
            for item in components
            for metric in item.metrics
        )
        return ProductIntelligenceScoreResult(
            score_id=score_id,
            job_id=job_id,
            product_id=projection.product_id,
            projection_id=projection.projection_id,
            materialization_id=projection.materialization_id,
            review_id=projection.review_id,
            selection_id=projection.selection_id,
            validation_id=projection.validation_id,
            completeness_id=projection.completeness_id,
            conflict_detection_id=projection.conflict_detection_id,
            normalization_id=projection.normalization_id,
            extraction_id=projection.extraction_id,
            classification_id=projection.classification_id,
            enrichment_id=enrichment.enrichment_id if enrichment else None,
            category=projection.category,
            schema_version=projection.schema_version,
            schema_fingerprint=projection.schema_fingerprint,
            projection_status=projection.status,
            overall_score_bp=overall,
            overall_score_percent=(overall + 50) // 100,
            grade=grade,
            components=components,
            strength_codes=strengths,
            improvement_codes=improvements,
            top_improvement_codes=top,
            metrics=metrics,
            policy_version=POLICY_VERSION,
            engine="deterministic-product-intelligence-scorer-v1",
            engine_version="1.0",
            created_at=created_at,
        )

    @staticmethod
    def _validate_lineage(projection: CommerceCatalogProjection, *items: object) -> None:
        fields = (
            "product_id",
            "category",
            "schema_version",
            "schema_fingerprint",
            "classification_id",
            "extraction_id",
            "normalization_id",
        )
        if any(
            any(getattr(item, field) != getattr(projection, field) for field in fields)
            for item in items
        ):
            raise ProductIntelligenceLineageMismatchError()
        expected = {
            "materialization_id": projection.materialization_id,
            "review_id": projection.review_id,
            "selection_id": projection.selection_id,
            "validation_id": projection.validation_id,
            "completeness_id": projection.completeness_id,
            "conflict_detection_id": projection.conflict_detection_id,
        }
        if any(
            hasattr(item, field) and getattr(item, field) != value
            for item in items
            for field, value in expected.items()
        ):
            raise ProductIntelligenceLineageMismatchError()
        review = next((item for item in items if isinstance(item, ProductReviewSession)), None)
        if review is None or review.status is not ProductReviewSessionStatus.COMPLETED:
            raise ProductIntelligenceLineageMismatchError()
