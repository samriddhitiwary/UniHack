"""Deterministic structured attribute extraction tests."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.core.exceptions import StructuredAttributeExtractionLimitExceededError
from app.domain.attribute_extraction import (
    AttributeExtractionEvidence,
    AttributeExtractionEvidenceType,
    AttributeMatchType,
    AttributeValueParseStatus,
)
from app.domain.category_schemas.builtins import (
    centrifugal_pump_schema_v1,
    induction_motor_schema_v1,
)
from app.services.structured_attribute_extraction_engine import (
    StructuredAttributeExtractionEngine,
)

SOURCE = UUID("11111111-1111-4111-8111-111111111111")
NOW = datetime(2026, 8, 13, tzinfo=UTC)


def evidence(
    text: str,
    *,
    identifier: int = 1,
    location: str = "line=1",
    label: str | None = None,
    value: str | None = None,
    quality: int = 9_000,
) -> AttributeExtractionEvidence:
    return AttributeExtractionEvidence(
        evidence_id=f"evidence-{identifier:06d}",
        source_id=SOURCE,
        evidence_type=AttributeExtractionEvidenceType.DIRECT_TEXT,
        text=text,
        location=location,
        source_quality_bp=quality,
        order=identifier,
        label_hint=label,
        value_hint=value,
    )


def test_extracts_typed_raw_candidates_and_preserves_units() -> None:
    candidates, warnings, duplicates = StructuredAttributeExtractionEngine().extract(
        schema=induction_motor_schema_v1(),
        evidence=(evidence("Rated Power: 5.5 kW"), evidence("Speed: 1450 rpm", identifier=2)),
        now=NOW,
    )
    assert [item.attribute_name for item in candidates] == ["ratedPower", "speedRpm"]
    assert candidates[0].raw_value == "5.5" and candidates[0].raw_unit == "kW"
    assert candidates[1].raw_value == "1450" and candidates[1].raw_unit == "rpm"
    assert all(item.parse_status is AttributeValueParseStatus.PARSED for item in candidates)
    assert warnings == () and duplicates == 0


def test_contextual_table_hint_missing_value_and_confidence_formula() -> None:
    candidates, warnings, _ = StructuredAttributeExtractionEngine().extract(
        schema=induction_motor_schema_v1(),
        evidence=(evidence("Voltage |", label="Voltage", value=None, quality=9_500),),
        now=NOW,
    )
    assert candidates[0].match_type is AttributeMatchType.CONTEXTUAL
    assert candidates[0].parse_status is AttributeValueParseStatus.MISSING_VALUE
    assert candidates[0].confidence_bp == 8_500 * 9_500 * 7_000 // 100_000_000
    assert warnings == ("ATTRIBUTE_VALUE_MISSING",)


def test_unknown_units_are_not_converted_or_accepted_as_parsed() -> None:
    candidates, _, _ = StructuredAttributeExtractionEngine().extract(
        schema=induction_motor_schema_v1(), evidence=(evidence("Voltage: 415 volts"),), now=NOW
    )
    assert candidates[0].raw_value == "415 volts" and candidates[0].raw_unit is None
    assert candidates[0].parse_status is AttributeValueParseStatus.RAW_TEXT


def test_exact_duplicate_is_suppressed_but_conflicting_locations_are_preserved() -> None:
    engine = StructuredAttributeExtractionEngine()
    candidates, _, duplicates = engine.extract(
        schema=induction_motor_schema_v1(),
        evidence=(
            evidence("Frequency: 50 Hz"),
            evidence("Frequency: 50 Hz", identifier=2),
            evidence("Frequency: 60 Hz", identifier=3, location="line=2"),
        ),
        now=NOW,
    )
    assert len(candidates) == 2 and duplicates == 1
    assert {item.raw_value for item in candidates} == {"50", "60"}


def test_candidate_limit_is_controlled() -> None:
    with pytest.raises(StructuredAttributeExtractionLimitExceededError):
        StructuredAttributeExtractionEngine(max_candidates=1).extract(
            schema=induction_motor_schema_v1(),
            evidence=(evidence("Voltage: 415 V"), evidence("Frequency: 50 Hz", identifier=2)),
        )


def test_pump_alias_normalization_and_missing_expected_unit() -> None:
    candidates, _, _ = StructuredAttributeExtractionEngine().extract(
        schema=centrifugal_pump_schema_v1(),
        evidence=(evidence("Flow-rate: 125"),),
        now=NOW,
    )
    assert candidates[0].attribute_name == "flowRate"
    assert candidates[0].match_type is AttributeMatchType.NORMALIZED
    assert candidates[0].raw_value == "125" and candidates[0].raw_unit is None
