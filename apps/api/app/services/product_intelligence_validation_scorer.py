"""Final-reviewed-attribute validation quality scoring."""

from app.core.exceptions import ProductIntelligenceRequiredComponentInvalidError
from app.domain.attribute_validation import AttributeValidationResult, CandidateValidationStatus
from app.domain.product_intelligence import (
    ComponentEvaluationStatus,
    ProductIntelligenceComponent,
    ProductIntelligenceComponentScore,
    ProductIntelligenceMetric,
)
from app.domain.reviewed_attributes import FinalAttributeOrigin, FinalReviewedAttributeSet
from app.services.product_intelligence_policy import BASE_WEIGHTS, weighted_mean


class ProductIntelligenceValidationScorer:
    def score(
        self, materialization: FinalReviewedAttributeSet, validation: AttributeValidationResult
    ) -> ProductIntelligenceComponentScore:
        assessments = {item.normalized_candidate_id: item for item in validation.assessments}
        values = []
        warnings = overrides = 0
        for attribute in materialization.attributes:
            weight = 2 if attribute.required else 1
            if attribute.origin is FinalAttributeOrigin.HUMAN_OVERRIDE:
                point = 8_500
                overrides += 1
            else:
                assessment = assessments.get(attribute.candidate_id or "")
                if assessment is None or assessment.status not in {
                    CandidateValidationStatus.VALID,
                    CandidateValidationStatus.VALID_WITH_WARNINGS,
                }:
                    raise ProductIntelligenceRequiredComponentInvalidError()
                point = 10_000 if assessment.status is CandidateValidationStatus.VALID else 8_000
                warnings += assessment.status is CandidateValidationStatus.VALID_WITH_WARNINGS
            values.append((point, weight))
        raw = weighted_mean(tuple(values))
        return ProductIntelligenceComponentScore(
            component=ProductIntelligenceComponent.VALIDATION_QUALITY,
            status=ComponentEvaluationStatus.EVALUATED,
            raw_score_bp=raw,
            base_weight_bp=BASE_WEIGHTS[ProductIntelligenceComponent.VALIDATION_QUALITY],
            normalized_weight_bp=0,
            weighted_contribution_bp=0,
            strength_codes=tuple(
                code
                for code, ok in (
                    ("ALL_FINAL_ATTRIBUTES_VALIDATED", True),
                    ("NO_VALIDATION_ERRORS", True),
                    ("REQUIRED_ATTRIBUTES_FULLY_VALIDATED", True),
                )
                if ok
            ),
            improvement_codes=tuple(
                code
                for code, ok in (
                    ("VALIDATION_WARNINGS_PRESENT", bool(warnings)),
                    ("HUMAN_VALIDATED_OVERRIDES_PRESENT", bool(overrides)),
                )
                if ok
            ),
            metrics=(
                ProductIntelligenceMetric(
                    name="validAttributeCount", value=len(values) - warnings - overrides
                ),
                ProductIntelligenceMetric(name="warningAttributeCount", value=warnings),
                ProductIntelligenceMetric(name="humanValidatedOverrideCount", value=overrides),
            ),
        )
