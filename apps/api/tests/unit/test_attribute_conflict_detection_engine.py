from dataclasses import replace
from uuid import uuid4

import pytest

from app.core.exceptions import AttributeConflictCandidateLimitExceededError
from app.domain.attribute_conflicts import (
    AttributeConflictType,
    AttributeConsensusStatus,
    ConflictDetectionResultStatus,
)
from app.domain.attribute_normalization import AttributeNormalizationResult
from app.domain.category_schemas import AttributeDataType
from app.domain.category_schemas.builtins import induction_motor_schema_v1
from app.services.attribute_conflict_detection_engine import AttributeConflictDetectionEngine
from app.services.attribute_normalization_engine import AttributeNormalizationEngine
from tests.fixtures.attribute_normalization import NOW, candidate, extraction


def normalized(*items):
    schema = induction_motor_schema_v1()
    sources = tuple(
        candidate(schema, name, value, unit, index=index)
        for index, (name, value, unit) in enumerate(items, 1)
    )
    extracted = extraction(schema, sources)
    return AttributeNormalizationEngine().normalize(
        job_id=uuid4(), extraction_result=extracted, schema=schema, now=NOW
    )


def detect(result):
    return AttributeConflictDetectionEngine().detect(
        job_id=uuid4(), normalization_result=result, now=NOW
    )


def test_exact_tolerance_and_conflict_are_detected_without_selecting_a_winner() -> None:
    result = normalized(
        ("voltage", "415", "V"),
        ("voltage", "415", "V"),
        ("ratedPower", "5.5", "kW"),
        ("ratedPower", "5.51", "kW"),
        ("current", "10", "A"),
        ("current", "11", "A"),
    )
    detected = detect(result)
    voltage, power, current = detected.attributes
    assert voltage.status is AttributeConsensusStatus.AGREEMENT
    assert voltage.consensus_confidence_bp == 10_000
    assert power.status is AttributeConsensusStatus.AGREEMENT_WITH_TOLERANCE
    assert power.consensus_confidence_bp == 9_000
    assert current.status is AttributeConsensusStatus.CONFLICT
    assert current.conflict_type is AttributeConflictType.VALUE_CONFLICT
    assert len(current.groups) == 2
    assert detected.status is ConflictDetectionResultStatus.CONFLICTS_FOUND


def test_three_candidates_do_not_use_majority_resolution() -> None:
    detected = detect(
        normalized(
            ("voltage", "415", "V"),
            ("voltage", "415", "V"),
            ("voltage", "440", "V"),
        )
    )
    consensus = detected.attributes[0]
    assert consensus.status is AttributeConsensusStatus.CONFLICT
    assert consensus.candidate_count == 3 and consensus.agreement_group_count == 2


def test_unit_missing_mixed_with_unit_bearing_is_indeterminate() -> None:
    consensus = detect(
        normalized(("ratedPower", "5.5", None), ("ratedPower", "5.5", "kW"))
    ).attributes[0]
    assert consensus.status is AttributeConsensusStatus.INDETERMINATE
    assert consensus.conflict_type is AttributeConflictType.UNIT_INDETERMINATE
    assert consensus.consensus_confidence_bp == 5_000


def test_invalid_candidates_are_excluded_and_reported_as_mixed_validity() -> None:
    consensus = detect(normalized(("voltage", "415", "V"), ("voltage", "bad", "V"))).attributes[0]
    assert consensus.status is AttributeConsensusStatus.SINGLE_CANDIDATE
    assert consensus.excluded_candidate_count == 1
    assert consensus.warning_codes == (AttributeConflictType.MIXED_VALIDITY.value,)


def test_no_valid_candidates_and_empty_results_have_explicit_statuses() -> None:
    invalid = detect(normalized(("voltage", "bad", "V")))
    assert invalid.attributes[0].status is AttributeConsensusStatus.NO_VALID_CANDIDATES
    assert invalid.status is ConflictDetectionResultStatus.COMPLETED_WITH_WARNINGS

    base = normalized(("voltage", "415", "V"))
    empty = AttributeNormalizationResult.create(
        job_id=uuid4(),
        product_id=base.product_id,
        extraction_id=base.extraction_id,
        classification_id=base.classification_id,
        category=base.category,
        schema_version=base.schema_version,
        schema_fingerprint=base.schema_fingerprint,
        candidates=(),
        now=NOW,
    )
    assert detect(empty).status is ConflictDetectionResultStatus.NO_COMPARABLE_ATTRIBUTES


def test_same_source_confidence_and_numeric_zero_safety() -> None:
    base = normalized(("current", "0", "A"), ("current", "0", "A"))
    candidates = (
        base.candidates[0],
        replace(base.candidates[1], source_id=base.candidates[0].source_id),
    )
    result = AttributeNormalizationResult.create(
        job_id=base.job_id,
        product_id=base.product_id,
        extraction_id=base.extraction_id,
        classification_id=base.classification_id,
        category=base.category,
        schema_version=base.schema_version,
        schema_fingerprint=base.schema_fingerprint,
        candidates=candidates,
        now=NOW,
    )
    consensus = detect(result).attributes[0]
    assert consensus.status is AttributeConsensusStatus.AGREEMENT
    assert consensus.consensus_confidence_bp == 8_500


def test_limits_are_enforced() -> None:
    result = normalized(("voltage", "415", "V"), ("voltage", "440", "V"))
    with pytest.raises(AttributeConflictCandidateLimitExceededError):
        AttributeConflictDetectionEngine(max_candidates_per_attribute=1).detect(
            job_id=uuid4(), normalization_result=result, now=NOW
        )
    with pytest.raises(ValueError):
        AttributeConflictDetectionEngine(max_attributes=0)


@pytest.mark.parametrize(
    ("data_type", "left", "right", "expected"),
    [
        (AttributeDataType.TEXT, "  IP55 ", "ip55", AttributeConsensusStatus.AGREEMENT),
        (AttributeDataType.TEXT, "cast iron", "grey cast iron", AttributeConsensusStatus.CONFLICT),
        (AttributeDataType.BOOLEAN, "true", "TRUE", AttributeConsensusStatus.AGREEMENT),
        (AttributeDataType.BOOLEAN, "true", "false", AttributeConsensusStatus.CONFLICT),
        (AttributeDataType.ENUM, "B3", "b3", AttributeConsensusStatus.AGREEMENT),
        (AttributeDataType.ENUM, "B3", "B5", AttributeConsensusStatus.CONFLICT),
        (AttributeDataType.INTEGER, "3", "3", AttributeConsensusStatus.AGREEMENT),
        (AttributeDataType.INTEGER, "3", "1", AttributeConsensusStatus.CONFLICT),
    ],
)
def test_text_boolean_enum_and_integer_comparison(data_type, left, right, expected) -> None:
    base = normalized(("voltage", "415", "V"), ("voltage", "440", "V"))
    candidates = tuple(
        replace(
            item,
            attribute_name="syntheticValue",
            attribute_display_name="Synthetic Value",
            data_type=data_type,
            normalized_value=value,
            normalized_unit=None,
        )
        for item, value in zip(base.candidates, (left, right), strict=True)
    )
    adjusted = AttributeNormalizationResult.create(
        job_id=base.job_id,
        product_id=base.product_id,
        extraction_id=base.extraction_id,
        classification_id=base.classification_id,
        category=base.category,
        schema_version=base.schema_version,
        schema_fingerprint=base.schema_fingerprint,
        candidates=candidates,
        now=NOW,
    )
    assert detect(adjusted).attributes[0].status is expected
