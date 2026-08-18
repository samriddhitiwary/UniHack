from dataclasses import replace
from decimal import Decimal

import pytest

from app.core.exceptions import AttributeValidationSchemaRuleInvalidError
from app.domain.attribute_normalization import NormalizationStatus
from app.domain.attribute_validation import CandidateValidationStatus, ValidationIssueType
from app.domain.category_schemas import (
    AttributeDataType,
    AttributeDefinition,
    AttributeValidationRules,
)
from app.services.attribute_numeric_validator import AttributeNumericValidator
from app.services.attribute_pattern_validator import AttributePatternValidator
from app.services.attribute_unit_validator import AttributeUnitValidator
from app.services.attribute_validation_engine import AttributeValidationEngine
from tests.unit.test_attribute_validation_engine import normalized


def definition(data_type, *, rules=None):
    return AttributeDefinition(
        attribute_id="testValue",
        canonical_name="testValue",
        display_name="Test Value",
        description="Synthetic validator field.",
        data_type=data_type,
        required=True,
        validation_rules=rules or AttributeValidationRules(),
    )


def test_number_decimal_and_integer_type_validation() -> None:
    numeric = AttributeNumericValidator()
    bounded = definition(
        AttributeDataType.NUMBER,
        rules=AttributeValidationRules(min_value=Decimal("0.1"), max_value=1),
    )
    assert numeric.validate("0.1", bounded) == ()
    assert numeric.validate("nan", bounded)[0].issue_type is ValidationIssueType.TYPE_INVALID
    assert (
        numeric.validate("3.5", definition(AttributeDataType.INTEGER))[0].message_code
        == "INTEGER_REQUIRED"
    )


def test_pattern_validator_uses_bounded_fullmatch() -> None:
    validator = AttributePatternValidator(max_pattern_characters=20)
    assert validator.validate("IP55", r"^IP[0-9]{2}$") == ()
    assert (
        validator.validate("xIP55", r"IP[0-9]{2}")[0].issue_type
        is ValidationIssueType.PATTERN_VIOLATION
    )
    with pytest.raises(AttributeValidationSchemaRuleInvalidError):
        validator.validate("value", "[")
    with pytest.raises(AttributeValidationSchemaRuleInvalidError):
        validator.validate("value", "x" * 21)


def test_boolean_enum_and_text_types_are_exact_and_schema_driven() -> None:
    engine = AttributeValidationEngine()
    boolean = definition(AttributeDataType.BOOLEAN)
    assert engine._type_and_rules("true", boolean) == ()
    assert engine._type_and_rules("TRUE", boolean)[0].message_code == "CANONICAL_BOOLEAN_REQUIRED"
    enum = definition(
        AttributeDataType.ENUM, rules=AttributeValidationRules(allowed_values=("B3", "B5"))
    )
    assert engine._type_and_rules("B3", enum) == ()
    assert (
        engine._type_and_rules("B9", enum)[0].issue_type
        is ValidationIssueType.ALLOWED_VALUE_VIOLATION
    )
    assert engine._type_and_rules("Mechanical Seal", definition(AttributeDataType.TEXT)) == ()
    assert (
        engine._type_and_rules(" ", definition(AttributeDataType.TEXT))[0].issue_type
        is ValidationIssueType.TYPE_INVALID
    )


def test_normalized_unit_must_match_schema_canonical_units() -> None:
    schema, result = normalized(("voltage", "415", "V"))
    candidate = replace(
        result.candidates[0],
        normalized_unit="rpm",
        normalization_status=NormalizationStatus.NORMALIZED,
    )
    definition_value = next(item for item in schema.attributes if item.canonical_name == "voltage")
    issue = AttributeUnitValidator().validate(candidate, definition_value)[0]
    assert issue.issue_type is ValidationIssueType.UNIT_UNSUPPORTED
    assert CandidateValidationStatus.INVALID.value == "INVALID"
