"""Versioned deterministic Product Intelligence Score policy."""

from app.domain.product_intelligence import ProductIntelligenceComponent

POLICY_VERSION = "product-intelligence-score-v1"
BASE_WEIGHTS = {
    ProductIntelligenceComponent.COMPLETENESS: 2_500,
    ProductIntelligenceComponent.VALIDATION_QUALITY: 2_000,
    ProductIntelligenceComponent.SOURCE_CORROBORATION: 2_000,
    ProductIntelligenceComponent.CONFLICT_HEALTH: 1_500,
    ProductIntelligenceComponent.REVIEW_QUALITY: 1_000,
    ProductIntelligenceComponent.AI_GROUNDING_QUALITY: 1_000,
}


def weighted_mean(values: tuple[tuple[int, int], ...]) -> int:
    total_weight = sum(weight for _, weight in values)
    if not total_weight:
        raise ValueError("a component requires at least one scoring unit")
    return sum(score * weight for score, weight in values) // total_weight
