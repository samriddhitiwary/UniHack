"""Small reviewed product-type attribute policy justified by challenge descriptions."""

from app.domain.unilog_attributes import UnilogAttributeProductTypeRule


def _rule(
    product_type: str,
    *,
    dimensions: tuple[str, ...] = (),
    grit: bool = False,
    quantity: bool = True,
    size: bool = False,
    priority: int = 50,
) -> UnilogAttributeProductTypeRule:
    semantic = (
        *dimensions,
        *(("Grit",) if grit else ()),
        *(("Package Quantity",) if quantity else ()),
    )
    return UnilogAttributeProductTypeRule(
        product_type=product_type,
        semantic_attributes=semantic,
        dimension_order=dimensions,
        supports_quantity=quantity,
        supports_grit=grit,
        map_dimensions_to_size=size,
        priority=priority,
    )


PRODUCT_TYPE_ATTRIBUTE_RULES = (
    _rule("Sanding Belt", dimensions=("Width", "Length"), grit=True, size=True, priority=100),
    _rule("Stikit Film", grit=True, priority=95),
    _rule("Sanding Disc", grit=True, priority=90),
    _rule("Abrasive Disc", grit=True, priority=90),
    _rule("Sanding Sponge", grit=True, priority=85),
    _rule("Metal Cut-Off Disc", priority=80),
    _rule("Masonry Cut-Off Disc", priority=80),
    _rule("Cut-Off Disc", priority=75),
    _rule("Cut and Grind Disc", priority=75),
    _rule("Grinding Wheel", priority=75),
    _rule("Decking", dimensions=("Thickness", "Width", "Length"), size=True, priority=70),
    _rule("Fascia", dimensions=("Thickness", "Width", "Length"), size=True, priority=70),
    _rule("Rail Panel", dimensions=("Width", "Length"), size=True, priority=65),
    _rule("Post Sleeve", dimensions=("Width", "Length"), size=True, priority=65),
    UnilogAttributeProductTypeRule(
        product_type="Dishwasher",
        semantic_attributes=(
            "Series",
            "Model",
            "Number of Wash Cycles",
            "Voltage Rating",
            "Amperage Rating",
            "Mounting Type",
            "Plug Type",
            "Size",
            "Depth With Door Open",
            "Minimum Height",
            "Maximum Height",
            "Sound Level",
            "Material",
            "Color",
            "Additional Information",
        ),
        dimension_order=(),
        supports_quantity=False,
        supports_grit=False,
        map_dimensions_to_size=False,
        priority=60,
    ),
)


class UnilogAttributeRuleRegistry:
    """Direct-indexed lookup for reviewed product-type attribute rules."""

    def __init__(
        self, rules: tuple[UnilogAttributeProductTypeRule, ...] = PRODUCT_TYPE_ATTRIBUTE_RULES
    ) -> None:
        self._by_type = {rule.product_type: rule for rule in rules}

    def get(self, product_type: str | None) -> UnilogAttributeProductTypeRule | None:
        return self._by_type.get(product_type or "")
