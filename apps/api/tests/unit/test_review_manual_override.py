"""Deterministic manual override normalization and validation tests."""

import pytest

from app.core.exceptions import ProductReviewManualOverrideInvalidError
from app.domain.category_schemas import (
    AttributeDataType,
    AttributeDefinition,
    AttributeValidationRules,
)
from app.domain.category_schemas.builtins import induction_motor_schema_v1
from app.services.review_manual_override import ReviewManualOverride


def definition(name: str):
    return next(
        item for item in induction_motor_schema_v1().attributes if item.canonical_name == name
    )


def test_numeric_override_converts_units_and_preserves_canonical_value() -> None:
    result = ReviewManualOverride().normalize_and_validate(
        definition=definition("ratedPower"), raw_value="5500", raw_unit="W"
    )
    assert (result.approved_value, result.approved_unit) == ("5.5", "kW")


def test_boolean_enum_and_text_are_deterministic() -> None:
    helper = ReviewManualOverride()
    boolean = AttributeDefinition(
        attribute_id="enabled",
        canonical_name="enabled",
        display_name="Enabled",
        description="Boolean test attribute.",
        data_type=AttributeDataType.BOOLEAN,
        required=True,
    )
    enum = AttributeDefinition(
        attribute_id="mode",
        canonical_name="mode",
        display_name="Mode",
        description="Enum test attribute.",
        data_type=AttributeDataType.ENUM,
        required=True,
        validation_rules=AttributeValidationRules(allowed_values=("AUTO", "MANUAL")),
    )
    assert (
        helper.normalize_and_validate(
            definition=boolean, raw_value="YES", raw_unit=None
        ).approved_value
        == "true"
    )
    assert (
        helper.normalize_and_validate(
            definition=enum, raw_value="manual", raw_unit=None
        ).approved_value
        == "MANUAL"
    )
    assert (
        helper.normalize_and_validate(
            definition=definition("insulationClass"), raw_value=" F ", raw_unit=None
        ).approved_value
        == "F"
    )


@pytest.mark.parametrize(
    ("name", "value", "unit"),
    [
        ("efficiency", "105", "%"),
        ("voltage", "430", None),
        ("ratedPower", "invalid", "kW"),
        ("ipRating", "unknown", None),
        ("phase", "3", "V"),
    ],
)
def test_invalid_manual_overrides_are_rejected(name: str, value: str, unit: str | None) -> None:
    with pytest.raises(ProductReviewManualOverrideInvalidError):
        ReviewManualOverride().normalize_and_validate(
            definition=definition(name), raw_value=value, raw_unit=unit
        )
