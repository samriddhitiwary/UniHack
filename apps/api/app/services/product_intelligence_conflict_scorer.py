"""Historical source-conflict health component scoring."""

from app.core.exceptions import ProductIntelligenceRequiredComponentInvalidError
from app.domain.attribute_conflicts import (
    AttributeConflictDetectionResult,
    AttributeConsensusStatus,
)
from app.domain.product_intelligence import (
    ComponentEvaluationStatus,
    ProductIntelligenceComponent,
    ProductIntelligenceComponentScore,
    ProductIntelligenceMetric,
)
from app.domain.reviewed_attributes import FinalAttributeOrigin, FinalReviewedAttributeSet
from app.services.product_intelligence_policy import BASE_WEIGHTS, weighted_mean


class ProductIntelligenceConflictScorer:
    def score(
        self,
        materialization: FinalReviewedAttributeSet,
        conflicts: AttributeConflictDetectionResult,
    ) -> ProductIntelligenceComponentScore:
        consensus = {item.attribute_name: item for item in conflicts.attributes}
        points = {
            AttributeConsensusStatus.AGREEMENT: 10_000,
            AttributeConsensusStatus.AGREEMENT_WITH_TOLERANCE: 9_500,
            AttributeConsensusStatus.SINGLE_CANDIDATE: 8_000,
        }
        values = []
        conflict_count = indeterminate = override_resolutions = 0
        for attribute in materialization.attributes:
            item = consensus.get(attribute.attribute_name)
            if item is None or item.status is AttributeConsensusStatus.NO_VALID_CANDIDATES:
                raise ProductIntelligenceRequiredComponentInvalidError()
            if item.status is AttributeConsensusStatus.CONFLICT:
                point = 6_000 if attribute.origin is FinalAttributeOrigin.HUMAN_OVERRIDE else 7_000
                conflict_count += 1
                override_resolutions += attribute.origin is FinalAttributeOrigin.HUMAN_OVERRIDE
            elif item.status is AttributeConsensusStatus.INDETERMINATE:
                point = 6_500
                indeterminate += 1
            else:
                point = points[item.status]
            values.append((point, 2 if attribute.required else 1))
        raw = weighted_mean(tuple(values))
        return ProductIntelligenceComponentScore(
            component=ProductIntelligenceComponent.CONFLICT_HEALTH,
            status=ComponentEvaluationStatus.EVALUATED,
            raw_score_bp=raw,
            base_weight_bp=BASE_WEIGHTS[ProductIntelligenceComponent.CONFLICT_HEALTH],
            normalized_weight_bp=0,
            weighted_contribution_bp=0,
            strength_codes=tuple(
                code
                for code, ok in (
                    ("NO_SOURCE_CONFLICTS", not conflict_count),
                    ("CONFLICTS_RESOLVED", bool(conflict_count)),
                    ("MOST_ATTRIBUTES_IN_AGREEMENT", conflicts.agreement_count * 2 >= len(values)),
                )
                if ok
            ),
            improvement_codes=tuple(
                code
                for code, ok in (
                    ("SOURCE_CONFLICTS_PRESENT", bool(conflict_count)),
                    ("HUMAN_CONFLICT_RESOLUTION_REQUIRED", bool(override_resolutions)),
                    ("INDETERMINATE_SOURCE_EVIDENCE_PRESENT", bool(indeterminate)),
                )
                if ok
            ),
            metrics=(
                ProductIntelligenceMetric(name="conflictedAttributeCount", value=conflict_count),
                ProductIntelligenceMetric(name="indeterminateAttributeCount", value=indeterminate),
                ProductIntelligenceMetric(
                    name="overrideResolvedConflictCount", value=override_resolutions
                ),
            ),
        )
