"""Final review-origin quality component scoring."""

from app.domain.product_intelligence import (
    ComponentEvaluationStatus,
    ProductIntelligenceComponent,
    ProductIntelligenceComponentScore,
    ProductIntelligenceMetric,
)
from app.domain.reviewed_attributes import FinalAttributeOrigin, FinalReviewedAttributeSet
from app.services.product_intelligence_policy import BASE_WEIGHTS, weighted_mean


class ProductIntelligenceReviewScorer:
    def score(
        self, materialization: FinalReviewedAttributeSet
    ) -> ProductIntelligenceComponentScore:
        points = {
            FinalAttributeOrigin.APPROVED_PROPOSED: 10_000,
            FinalAttributeOrigin.APPROVED_CANDIDATE: 8_500,
            FinalAttributeOrigin.HUMAN_OVERRIDE: 7_000,
        }
        values = tuple(
            (points[item.origin], 2 if item.required else 1) for item in materialization.attributes
        )
        overrides = sum(
            item.origin is FinalAttributeOrigin.HUMAN_OVERRIDE
            for item in materialization.attributes
        )
        candidates = sum(
            item.origin is FinalAttributeOrigin.APPROVED_CANDIDATE
            for item in materialization.attributes
        )
        proposed = sum(
            item.origin is FinalAttributeOrigin.APPROVED_PROPOSED
            for item in materialization.attributes
        )
        return ProductIntelligenceComponentScore(
            component=ProductIntelligenceComponent.REVIEW_QUALITY,
            status=ComponentEvaluationStatus.EVALUATED,
            raw_score_bp=weighted_mean(values),
            base_weight_bp=BASE_WEIGHTS[ProductIntelligenceComponent.REVIEW_QUALITY],
            normalized_weight_bp=0,
            weighted_contribution_bp=0,
            strength_codes=tuple(
                code
                for code, ok in (
                    ("MOST_ATTRIBUTES_AUTO_SELECTED", proposed * 2 >= len(values)),
                    ("NO_HUMAN_OVERRIDES", not overrides),
                    ("REVIEW_COMPLETED", True),
                )
                if ok
            ),
            improvement_codes=tuple(
                code
                for code, ok in (
                    ("HUMAN_OVERRIDES_PRESENT", bool(overrides)),
                    ("MANUAL_CANDIDATE_SELECTION_PRESENT", bool(candidates)),
                    ("HIGH_REVIEW_INTERVENTION", (overrides + candidates) * 2 > len(values)),
                )
                if ok
            ),
            metrics=(
                ProductIntelligenceMetric(name="humanOverrideCount", value=overrides),
                ProductIntelligenceMetric(name="manualCandidateSelectionCount", value=candidates),
                ProductIntelligenceMetric(name="approvedProposedCount", value=proposed),
            ),
        )
