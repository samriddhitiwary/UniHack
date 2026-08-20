"""Deterministic Product Intelligence strengths and action ordering."""

from app.domain.product_intelligence import ProductIntelligenceComponentScore

_ACTIONS = {
    "REQUIRED_ATTRIBUTES_MISSING": "COMPLETE_REQUIRED_ATTRIBUTES",
    "REQUIRED_ATTRIBUTES_INVALID": "RESOLVE_INVALID_REQUIRED_ATTRIBUTES",
    "REQUIRED_ATTRIBUTES_INDETERMINATE": "RESOLVE_INDETERMINATE_REQUIRED_ATTRIBUTES",
    "REQUIRED_ATTRIBUTES_CONFLICTED": "REDUCE_SOURCE_CONFLICTS",
    "SOURCE_CONFLICTS_PRESENT": "REDUCE_SOURCE_CONFLICTS",
    "HUMAN_CONFLICT_RESOLUTION_REQUIRED": "REDUCE_SOURCE_CONFLICTS",
    "REQUIRED_ATTRIBUTE_SINGLE_SOURCE": "ADD_INDEPENDENT_SOURCE_SUPPORT",
    "SINGLE_SOURCE_ATTRIBUTES_PRESENT": "ADD_INDEPENDENT_SOURCE_SUPPORT",
    "VALIDATION_WARNINGS_PRESENT": "RESOLVE_VALIDATION_WARNINGS",
    "HUMAN_OVERRIDES_PRESENT": "REDUCE_MANUAL_OVERRIDES",
    "HUMAN_VALIDATED_OVERRIDES_PRESENT": "REDUCE_MANUAL_OVERRIDES",
    "OPTIONAL_ATTRIBUTES_MISSING": "IMPROVE_OPTIONAL_ATTRIBUTE_COVERAGE",
    "AI_FACT_COVERAGE_LOW": "IMPROVE_AI_FACT_COVERAGE",
    "AI_ENRICHMENT_NOT_EVALUATED": "AI_ENRICHMENT_NOT_EVALUATED",
}

_PRIORITY = (
    "COMPLETE_REQUIRED_ATTRIBUTES",
    "RESOLVE_INVALID_REQUIRED_ATTRIBUTES",
    "RESOLVE_INDETERMINATE_REQUIRED_ATTRIBUTES",
    "REDUCE_SOURCE_CONFLICTS",
    "ADD_INDEPENDENT_SOURCE_SUPPORT",
    "RESOLVE_VALIDATION_WARNINGS",
    "REDUCE_MANUAL_OVERRIDES",
    "IMPROVE_OPTIONAL_ATTRIBUTE_COVERAGE",
    "IMPROVE_AI_FACT_COVERAGE",
)

_STRENGTHS = {
    "ALL_REQUIRED_ATTRIBUTES_RESOLVED": "CATALOG_REQUIRED_DATA_COMPLETE",
    "ALL_FINAL_ATTRIBUTES_VALIDATED": "CATALOG_FULLY_VALIDATED",
    "MULTI_SOURCE_SUPPORT_HIGH": "CATALOG_HIGHLY_CORROBORATED",
    "NO_SOURCE_CONFLICTS": "CATALOG_LOW_CONFLICT",
    "NO_HUMAN_OVERRIDES": "CATALOG_MINIMAL_MANUAL_INTERVENTION",
    "AI_CONTENT_FULLY_GROUNDED": "AI_CONTENT_FULLY_GROUNDED",
}


class ProductIntelligenceExplanationBuilder:
    def build(
        self, components: tuple[ProductIntelligenceComponentScore, ...]
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        component_strengths = tuple(code for item in components for code in item.strength_codes)
        strengths = tuple(
            dict.fromkeys(_STRENGTHS[code] for code in component_strengths if code in _STRENGTHS)
        )
        component_improvements = tuple(
            code for item in components for code in item.improvement_codes
        )
        improvements = tuple(
            dict.fromkeys(_ACTIONS.get(code, code) for code in component_improvements)
        )
        top = tuple(code for code in _PRIORITY if code in improvements)[:5]
        return strengths, improvements, top
