"""Fixed schema-compatible unit recognition and Decimal conversion."""

from dataclasses import dataclass
from decimal import Decimal

from app.domain.attribute_normalization.units import ATTRIBUTE_DIMENSIONS, UNIT_RULES
from app.domain.category_schemas import AttributeDefinition


def normalize_unit_alias(value: str) -> str:
    return " ".join(value.strip().replace("³", "3").casefold().split())


@dataclass(frozen=True, slots=True, kw_only=True)
class UnitNormalizationOutcome:
    value: Decimal
    normalized_unit: str
    conversion_applied: bool
    unit_canonicalization_applied: bool
    conversion_rule: str | None


class UnitNormalizer:
    def normalize(
        self, *, attribute: AttributeDefinition, value: Decimal, raw_unit: str
    ) -> UnitNormalizationOutcome | None:
        dimension = ATTRIBUTE_DIMENSIONS.get(attribute.canonical_name)
        if dimension is None:
            return None
        alias = normalize_unit_alias(raw_unit)
        rule = next(
            (
                candidate
                for candidate in UNIT_RULES
                if candidate.dimension is dimension
                and alias in {normalize_unit_alias(item) for item in candidate.aliases}
            ),
            None,
        )
        if rule is None:
            return None
        schema_units = {normalize_unit_alias(unit.symbol) for unit in attribute.allowed_units}
        if normalize_unit_alias(rule.source_unit) not in schema_units:
            return None
        converted = value * rule.factor
        conversion_applied = rule.conversion_rule is not None
        return UnitNormalizationOutcome(
            value=converted,
            normalized_unit=rule.canonical_unit,
            conversion_applied=conversion_applied,
            unit_canonicalization_applied=raw_unit.strip() != rule.canonical_unit,
            conversion_rule=rule.conversion_rule,
        )
