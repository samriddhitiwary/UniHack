"""Product intelligence component, status, and grade vocabularies."""

from enum import StrEnum


class ProductIntelligenceComponent(StrEnum):
    COMPLETENESS = "COMPLETENESS"
    VALIDATION_QUALITY = "VALIDATION_QUALITY"
    SOURCE_CORROBORATION = "SOURCE_CORROBORATION"
    CONFLICT_HEALTH = "CONFLICT_HEALTH"
    REVIEW_QUALITY = "REVIEW_QUALITY"
    AI_GROUNDING_QUALITY = "AI_GROUNDING_QUALITY"


class ComponentEvaluationStatus(StrEnum):
    EVALUATED = "EVALUATED"
    NOT_EVALUATED = "NOT_EVALUATED"


class ProductIntelligenceGrade(StrEnum):
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"
    CRITICAL = "CRITICAL"
