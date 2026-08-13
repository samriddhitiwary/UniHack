from uuid import uuid4

import pytest

from app.domain.attribute_normalization import (
    AttributeNormalizationResultStatus,
    NormalizationStatus,
)
from app.domain.category_schemas import (
    AttributeDataType,
    AttributeDefinition,
    AttributeValidationRules,
    CategoryAttributeSchema,
    CategoryAttributeSchemaStatus,
)
from app.domain.category_schemas.builtins import (
    centrifugal_pump_schema_v1,
    induction_motor_schema_v1,
)
from app.domain.products import ProductCategory
from app.services.attribute_normalization_engine import AttributeNormalizationEngine
from tests.fixtures.attribute_normalization import NOW, candidate, extraction


@pytest.mark.parametrize(
    ("schema_factory", "attribute", "raw_value", "raw_unit", "value", "unit", "rule"),
    [
        (induction_motor_schema_v1, "ratedPower", "5500", "W", "5.5", "kW", "W_TO_KW"),
        (induction_motor_schema_v1, "ratedPower", "10", "hp", "7.456999", "kW", "HP_TO_KW"),
        (centrifugal_pump_schema_v1, "flowRate", "100", "L/min", "6", "m3/h", "L_MIN_TO_M3_H"),
        (centrifugal_pump_schema_v1, "flowRate", "10", "GPM", "2.271247", "m3/h", "US_GPM_TO_M3_H"),
        (centrifugal_pump_schema_v1, "head", "100", "ft", "30.48", "m", "FT_TO_M"),
        (centrifugal_pump_schema_v1, "suctionSize", "2", "inch", "50.8", "mm", "IN_TO_MM"),
        (
            centrifugal_pump_schema_v1,
            "maximumPressure",
            "100",
            "PSI",
            "6.894757",
            "bar",
            "PSI_TO_BAR",
        ),
    ],
)
def test_required_decimal_unit_conversions(
    schema_factory, attribute, raw_value, raw_unit, value, unit, rule
) -> None:
    schema = schema_factory()
    source = candidate(schema, attribute, raw_value, raw_unit)
    result = AttributeNormalizationEngine().normalize(
        job_id=uuid4(), extraction_result=extraction(schema, (source,)), schema=schema, now=NOW
    )
    normalized = result.candidates[0]
    assert (normalized.normalized_value, normalized.normalized_unit) == (value, unit)
    assert normalized.normalization_status is NormalizationStatus.NORMALIZED_WITH_CONVERSION
    assert normalized.conversion_rule == rule and normalized.conversion_applied


@pytest.mark.parametrize(
    ("schema_factory", "attribute", "raw_value", "raw_unit", "value", "unit"),
    [
        (induction_motor_schema_v1, "ratedPower", "5.5", "KW", "5.5", "kW"),
        (induction_motor_schema_v1, "voltage", "415", "volts", "415", "V"),
        (induction_motor_schema_v1, "current", "10", "amps", "10", "A"),
        (induction_motor_schema_v1, "frequency", "50", "HZ", "50", "Hz"),
        (induction_motor_schema_v1, "speedRpm", "1440", "r/min", "1440", "rpm"),
        (induction_motor_schema_v1, "efficiency", "92", "percent", "92", "%"),
        (centrifugal_pump_schema_v1, "flowRate", "100", "m³/h", "100", "m3/h"),
    ],
)
def test_required_unit_aliases_are_canonicalized(
    schema_factory, attribute, raw_value, raw_unit, value, unit
) -> None:
    schema = schema_factory()
    result = AttributeNormalizationEngine().normalize(
        job_id=uuid4(),
        extraction_result=extraction(schema, (candidate(schema, attribute, raw_value, raw_unit),)),
        schema=schema,
        now=NOW,
    )
    item = result.candidates[0]
    assert (item.normalized_value, item.normalized_unit) == (value, unit)
    assert item.normalization_status is NormalizationStatus.NORMALIZED
    assert item.unit_canonicalization_applied and not item.conversion_applied


def test_missing_unsupported_malformed_and_fractional_integer_are_warning_outcomes() -> None:
    schema = induction_motor_schema_v1()
    sources = (
        candidate(schema, "ratedPower", "5.5", None, index=1),
        candidate(schema, "voltage", "415", "rpm", index=2),
        candidate(schema, "ratedPower", "five", "kW", index=3),
        candidate(schema, "phase", "3.5", None, index=4),
    )
    result = AttributeNormalizationEngine().normalize(
        job_id=uuid4(), extraction_result=extraction(schema, sources), schema=schema, now=NOW
    )
    assert [item.normalization_status for item in result.candidates] == [
        NormalizationStatus.UNIT_MISSING,
        NormalizationStatus.UNSUPPORTED_UNIT,
        NormalizationStatus.INVALID_VALUE,
        NormalizationStatus.INVALID_VALUE,
    ]
    assert result.status is AttributeNormalizationResultStatus.NORMALIZED_WITH_WARNINGS
    assert (
        result.candidates[0].normalized_value == "5.5"
        and result.candidates[0].normalized_unit is None
    )
    assert result.candidates[1].raw_unit == "rpm" and result.candidates[1].normalized_value is None


def _synthetic_schema(data_type, *, name="testValue", allowed=()):
    attribute = AttributeDefinition(
        attribute_id=name,
        canonical_name=name,
        display_name="Test Value",
        description="Synthetic normalization test value.",
        data_type=data_type,
        required=True,
        validation_rules=AttributeValidationRules(allowed_values=allowed),
    )
    return CategoryAttributeSchema.create(
        category=ProductCategory.INDUCTION_MOTOR,
        version=1,
        status=CategoryAttributeSchemaStatus.ACTIVE,
        description="Synthetic test schema.",
        attributes=(attribute,),
        now=NOW,
    )


def test_text_boolean_and_enum_normalization_are_conservative() -> None:
    ip_schema = _synthetic_schema(AttributeDataType.TEXT, name="ipRating")
    boolean_schema = _synthetic_schema(AttributeDataType.BOOLEAN)
    enum_schema = _synthetic_schema(AttributeDataType.ENUM, allowed=("B3", "B5"))
    cases = (
        (ip_schema, "  ip 55  ", "IP55", NormalizationStatus.NORMALIZED),
        (boolean_schema, "YES", "true", NormalizationStatus.NORMALIZED),
        (boolean_schema, "maybe", None, NormalizationStatus.INVALID_VALUE),
        (enum_schema, " b3 ", "B3", NormalizationStatus.NORMALIZED),
        (enum_schema, "B9", "B9", NormalizationStatus.RAW_TEXT_PRESERVED),
    )
    for schema, raw, expected, status in cases:
        source = candidate(schema, schema.attributes[0].canonical_name, raw, None)
        item = (
            AttributeNormalizationEngine()
            .normalize(
                job_id=uuid4(),
                extraction_result=extraction(schema, (source,)),
                schema=schema,
                now=NOW,
            )
            .candidates[0]
        )
        assert item.normalized_value == expected and item.normalization_status is status


def test_equivalent_and_conflicting_candidates_remain_separate_with_lineage() -> None:
    schema = induction_motor_schema_v1()
    sources = (
        candidate(schema, "ratedPower", "5500", "W", index=1),
        candidate(schema, "ratedPower", "5.5", "kW", index=2),
        candidate(schema, "voltage", "415", "V", index=3),
        candidate(schema, "voltage", "440", "V", index=4),
    )
    extraction_result = extraction(schema, sources)
    result = AttributeNormalizationEngine().normalize(
        job_id=uuid4(), extraction_result=extraction_result, schema=schema, now=NOW
    )
    assert len(result.candidates) == 4
    assert [item.normalized_value for item in result.candidates[:2]] == ["5.5", "5.5"]
    assert [item.normalized_value for item in result.candidates[2:]] == ["415", "440"]
    assert all(
        item.source_extraction_id == extraction_result.extraction_id for item in result.candidates
    )
    assert [item.source_candidate_id for item in result.candidates] == [
        item.candidate_id for item in sources
    ]


def test_no_candidates_is_successful() -> None:
    schema = induction_motor_schema_v1()
    result = AttributeNormalizationEngine().normalize(
        job_id=uuid4(), extraction_result=extraction(schema, ()), schema=schema, now=NOW
    )
    assert result.status is AttributeNormalizationResultStatus.NO_CANDIDATES


def test_unitless_number_and_additional_text_canonicalizations() -> None:
    number_schema = _synthetic_schema(AttributeDataType.NUMBER)
    insulation_schema = _synthetic_schema(AttributeDataType.TEXT, name="insulationClass")
    duty_schema = _synthetic_schema(AttributeDataType.TEXT, name="duty")
    cases = (
        (number_schema, "testValue", "+3.00", "3"),
        (insulation_schema, "insulationClass", "Class f", "F"),
        (duty_schema, "duty", "s1", "S1"),
    )
    for schema, name, raw, expected in cases:
        item = (
            AttributeNormalizationEngine()
            .normalize(
                job_id=uuid4(),
                extraction_result=extraction(schema, (candidate(schema, name, raw, None),)),
                schema=schema,
                now=NOW,
            )
            .candidates[0]
        )
        assert item.normalized_value == expected
