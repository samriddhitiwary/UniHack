"""Deterministic normalization and schema validation for human overrides."""

from dataclasses import dataclass
from decimal import Decimal

from app.core.exceptions import ProductReviewManualOverrideInvalidError
from app.domain.category_schemas import AttributeDataType, AttributeDefinition
from app.services.attribute_pattern_validator import AttributePatternValidator
from app.services.numeric_normalizer import NumericNormalizer
from app.services.unit_normalizer import UnitNormalizer


@dataclass(frozen=True, slots=True)
class ManualOverrideOutcome:
    approved_value: str
    approved_unit: str | None


class ReviewManualOverride:
    def __init__(self, *, max_value_characters: int = 10_000) -> None:
        self._max_value = max_value_characters
        self._numeric = NumericNormalizer()
        self._units = UnitNormalizer()
        self._patterns = AttributePatternValidator()

    def normalize_and_validate(
        self,
        *,
        definition: AttributeDefinition,
        raw_value: str,
        raw_unit: str | None,
    ) -> ManualOverrideOutcome:
        if not raw_value or len(raw_value) > self._max_value:
            raise ProductReviewManualOverrideInvalidError()
        if definition.data_type in {AttributeDataType.NUMBER, AttributeDataType.INTEGER}:
            value = self._numeric.parse(raw_value)
            if value is None or (
                definition.data_type is AttributeDataType.INTEGER
                and value != value.to_integral_value()
            ):
                raise ProductReviewManualOverrideInvalidError()
            unit: str | None = None
            if definition.allowed_units:
                if raw_unit is None:
                    raise ProductReviewManualOverrideInvalidError()
                outcome = self._units.normalize(
                    attribute=definition, value=value, raw_unit=raw_unit
                )
                if outcome is None:
                    raise ProductReviewManualOverrideInvalidError()
                value = self._numeric.round_conversion(outcome.value)
                unit = outcome.normalized_unit
            elif raw_unit is not None:
                raise ProductReviewManualOverrideInvalidError()
            canonical = self._numeric.canonical(value)
            self._validate_rules(definition, canonical, value)
            return ManualOverrideOutcome(canonical, unit)
        if raw_unit is not None:
            raise ProductReviewManualOverrideInvalidError()
        canonical = "\n".join(
            " ".join(line.split())
            for line in raw_value.replace("\r\n", "\n").replace("\r", "\n").strip().split("\n")
        )
        if not canonical:
            raise ProductReviewManualOverrideInvalidError()
        if definition.data_type is AttributeDataType.BOOLEAN:
            token = canonical.casefold()
            if token in {"true", "yes", "y", "1"}:
                canonical = "true"
            elif token in {"false", "no", "n", "0"}:
                canonical = "false"
            else:
                raise ProductReviewManualOverrideInvalidError()
        elif definition.data_type is AttributeDataType.ENUM:
            allowed = {item.casefold(): item for item in definition.validation_rules.allowed_values}
            if canonical.casefold() not in allowed:
                raise ProductReviewManualOverrideInvalidError()
            canonical = allowed[canonical.casefold()]
        self._validate_rules(definition, canonical, None)
        return ManualOverrideOutcome(canonical, None)

    def _validate_rules(
        self, definition: AttributeDefinition, value: str, number: Decimal | None
    ) -> None:
        rules = definition.validation_rules
        if number is not None:
            if rules.min_value is not None and number < Decimal(str(rules.min_value)):
                raise ProductReviewManualOverrideInvalidError()
            if rules.max_value is not None and number > Decimal(str(rules.max_value)):
                raise ProductReviewManualOverrideInvalidError()
        if rules.allowed_values and value not in rules.allowed_values:
            raise ProductReviewManualOverrideInvalidError()
        if self._patterns.validate(value, rules.pattern):
            raise ProductReviewManualOverrideInvalidError()
