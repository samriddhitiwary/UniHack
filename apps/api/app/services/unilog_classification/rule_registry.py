"""Explicit product-type-dependent interpretation rules."""

DIMENSION_RULES: dict[str, tuple[str, ...]] = {
    # Challenge descriptions consistently express Sanding Belt dimensions as width x length.
    "Sanding Belt": ("Width", "Length"),
}


class UnilogProductTypeRuleRegistry:
    """Read-only registry for the small reviewed set of type-specific semantic rules."""

    @staticmethod
    def dimension_interpretation(product_type: str | None) -> tuple[str, ...] | None:
        return DIMENSION_RULES.get(product_type or "")
