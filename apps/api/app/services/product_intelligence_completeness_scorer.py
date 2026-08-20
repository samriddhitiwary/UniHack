"""Required-dominant completeness component scoring."""

from app.domain.attribute_completeness import AttributeCompletenessResult
from app.domain.product_intelligence import (
    ComponentEvaluationStatus,
    ProductIntelligenceComponent,
    ProductIntelligenceComponentScore,
    ProductIntelligenceMetric,
)
from app.services.product_intelligence_policy import BASE_WEIGHTS


class ProductIntelligenceCompletenessScorer:
    def score(self, result: AttributeCompletenessResult) -> ProductIntelligenceComponentScore:
        optional_bp = (
            10_000
            if result.optional_attribute_count == 0
            else result.optional_resolved_count * 10_000 // result.optional_attribute_count
        )
        raw = (
            result.required_resolved_bp
            if result.optional_attribute_count == 0
            else (result.required_resolved_bp * 8_500 + optional_bp * 1_500) // 10_000
        )
        strengths = []
        improvements = []
        if result.required_missing_count:
            improvements.append("REQUIRED_ATTRIBUTES_MISSING")
        if result.required_conflicted_count:
            improvements.append("REQUIRED_ATTRIBUTES_CONFLICTED")
        if result.required_invalid_count:
            improvements.append("REQUIRED_ATTRIBUTES_INVALID")
        if result.required_indeterminate_count:
            improvements.append("REQUIRED_ATTRIBUTES_INDETERMINATE")
        if result.optional_missing_count:
            improvements.append("OPTIONAL_ATTRIBUTES_MISSING")
        if result.required_resolved_count == result.required_attribute_count:
            strengths.append("ALL_REQUIRED_ATTRIBUTES_RESOLVED")
        if result.required_verified_count == result.required_attribute_count:
            strengths.append("ALL_REQUIRED_ATTRIBUTES_VERIFIED")
        if optional_bp >= 8_000:
            strengths.append("OPTIONAL_ATTRIBUTE_COVERAGE_HIGH")
        metric_values = {
            "requiredAttributeCount": result.required_attribute_count,
            "requiredResolvedCount": result.required_resolved_count,
            "requiredVerifiedCount": result.required_verified_count,
            "requiredMissingCount": result.required_missing_count,
            "requiredConflictedCount": result.required_conflicted_count,
            "requiredIndeterminateCount": result.required_indeterminate_count,
            "requiredInvalidCount": result.required_invalid_count,
            "requiredResolvedBp": result.required_resolved_bp,
            "optionalAttributeCount": result.optional_attribute_count,
            "optionalResolvedCount": result.optional_resolved_count,
            "optionalMissingCount": result.optional_missing_count,
            "optionalResolvedBp": optional_bp,
        }
        return ProductIntelligenceComponentScore(
            component=ProductIntelligenceComponent.COMPLETENESS,
            status=ComponentEvaluationStatus.EVALUATED,
            raw_score_bp=raw,
            base_weight_bp=BASE_WEIGHTS[ProductIntelligenceComponent.COMPLETENESS],
            normalized_weight_bp=0,
            weighted_contribution_bp=0,
            strength_codes=tuple(strengths),
            improvement_codes=tuple(improvements),
            metrics=tuple(
                ProductIntelligenceMetric(name=k, value=v) for k, v in metric_values.items()
            ),
        )
