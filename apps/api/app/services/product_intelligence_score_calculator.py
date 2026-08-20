"""Integer-only Product Intelligence weight normalization and score calculation."""

from dataclasses import replace

from app.core.exceptions import ProductIntelligenceWeightInvalidError
from app.domain.product_intelligence import (
    ComponentEvaluationStatus,
    ProductIntelligenceComponent,
    ProductIntelligenceComponentScore,
    ProductIntelligenceGrade,
)


class ProductIntelligenceScoreCalculator:
    def calculate(
        self, components: tuple[ProductIntelligenceComponentScore, ...]
    ) -> tuple[tuple[ProductIntelligenceComponentScore, ...], int, ProductIntelligenceGrade]:
        if tuple(item.component for item in components) != tuple(ProductIntelligenceComponent):
            raise ProductIntelligenceWeightInvalidError()
        evaluated = [
            item for item in components if item.status is ComponentEvaluationStatus.EVALUATED
        ]
        total = sum(item.base_weight_bp for item in evaluated)
        if not evaluated or total <= 0:
            raise ProductIntelligenceWeightInvalidError()
        weights = {item.component: item.base_weight_bp * 10_000 // total for item in evaluated}
        remainder = 10_000 - sum(weights.values())
        priority = sorted(
            evaluated,
            key=lambda item: (
                -item.base_weight_bp,
                tuple(ProductIntelligenceComponent).index(item.component),
            ),
        )
        for item in priority[:remainder]:
            weights[item.component] += 1
        normalized = tuple(
            replace(
                item,
                normalized_weight_bp=weights.get(item.component, 0),
                weighted_contribution_bp=(item.raw_score_bp or 0)
                * weights.get(item.component, 0)
                // 10_000,
            )
            for item in components
        )
        overall = max(0, min(10_000, sum(item.weighted_contribution_bp for item in normalized)))
        return normalized, overall, self.grade(overall)

    @staticmethod
    def grade(score_bp: int) -> ProductIntelligenceGrade:
        if score_bp >= 9_000:
            return ProductIntelligenceGrade.EXCELLENT
        if score_bp >= 8_000:
            return ProductIntelligenceGrade.GOOD
        if score_bp >= 6_500:
            return ProductIntelligenceGrade.FAIR
        if score_bp >= 5_000:
            return ProductIntelligenceGrade.POOR
        return ProductIntelligenceGrade.CRITICAL
