from dataclasses import replace
from uuid import uuid4

import pytest

from app.core.exceptions import AttributeSelectionLineageMismatchError
from app.domain.attribute_normalization import AttributeNormalizationResult
from app.domain.attribute_selection import (
    AttributeSelectionStatus,
    ProductReviewStatus,
    SelectionReasonCode,
)
from app.domain.category_schemas.builtins import induction_motor_schema_v1
from app.services.attribute_completeness_engine import AttributeCompletenessEngine
from app.services.attribute_conflict_detection_engine import AttributeConflictDetectionEngine
from app.services.attribute_normalization_engine import AttributeNormalizationEngine
from app.services.attribute_selection_engine import AttributeSelectionEngine
from app.services.attribute_validation_engine import AttributeValidationEngine
from tests.fixtures.attribute_normalization import NOW, candidate, extraction


def pipeline(*items, normalized_result=None):
    schema = induction_motor_schema_v1()
    normalization = normalized_result
    if normalization is None:
        sources = tuple(
            candidate(schema, name, value, unit, index=index)
            for index, (name, value, unit) in enumerate(items, 1)
        )
        normalization = AttributeNormalizationEngine().normalize(
            job_id=uuid4(), extraction_result=extraction(schema, sources), schema=schema, now=NOW
        )
    conflict = AttributeConflictDetectionEngine().detect(
        job_id=uuid4(), normalization_result=normalization, now=NOW
    )
    validation = AttributeValidationEngine().validate(
        job_id=uuid4(), normalization_result=normalization, schema=schema, now=NOW
    )
    completeness = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(), conflict_result=conflict, schema=schema, now=NOW
    )
    selection = AttributeSelectionEngine().select(
        job_id=uuid4(),
        conflict_result=conflict,
        validation_result=validation,
        completeness_result=completeness,
        normalization_result=normalization,
        now=NOW,
    )
    return schema, normalization, conflict, validation, completeness, selection


def attr(result, name):
    return next(item for item in result.attributes if item.attribute_name == name)


def test_exact_and_converted_multi_source_agreement_auto_select() -> None:
    *_, exact = pipeline(("ratedPower", "5.5", "kW"), ("ratedPower", "5.5", "kW"))
    power = attr(exact, "ratedPower")
    assert power.selection_status is AttributeSelectionStatus.AUTO_SELECTED
    assert (power.proposed_value, power.proposed_unit) == ("5.5", "kW")
    assert power.selection_confidence_bp == 10_000
    assert len(power.supporting_candidate_ids) == 2
    assert power.reason_codes == (SelectionReasonCode.MULTI_SOURCE_EXACT_AGREEMENT,)

    *_, converted = pipeline(("ratedPower", "5500", "W"), ("ratedPower", "5.5", "kW"))
    converted_power = attr(converted, "ratedPower")
    assert converted_power.selection_status is AttributeSelectionStatus.AUTO_SELECTED
    assert converted_power.proposed_value == "5.5" and converted_power.proposed_unit == "kW"


def test_tolerance_agreement_auto_selects_ranked_candidate_without_averaging() -> None:
    *_, result = pipeline(("ratedPower", "5.5", "kW"), ("ratedPower", "5.51", "kW"))
    power = attr(result, "ratedPower")
    assert power.selection_status is AttributeSelectionStatus.AUTO_SELECTED
    assert power.selection_confidence_bp == 9_000
    assert power.proposed_value in {"5.5", "5.51"}
    assert power.reason_codes == (SelectionReasonCode.MULTI_SOURCE_TOLERANCE_AGREEMENT,)


def test_single_same_source_conflict_and_three_candidate_majority_require_review() -> None:
    *_, single = pipeline(("voltage", "415", "V"))
    assert attr(single, "voltage").reason_codes == (SelectionReasonCode.SINGLE_SOURCE_ONLY,)

    schema = induction_motor_schema_v1()
    sources = tuple(candidate(schema, "voltage", "415", "V", index=i) for i in (1, 2))
    normalization = AttributeNormalizationEngine().normalize(
        job_id=uuid4(), extraction_result=extraction(schema, sources), schema=schema, now=NOW
    )
    same_source = tuple(
        replace(item, source_id=normalization.candidates[0].source_id)
        for item in normalization.candidates
    )
    normalization = AttributeNormalizationResult.create(
        job_id=uuid4(),
        product_id=normalization.product_id,
        extraction_id=normalization.extraction_id,
        classification_id=normalization.classification_id,
        category=normalization.category,
        schema_version=normalization.schema_version,
        schema_fingerprint=normalization.schema_fingerprint,
        candidates=same_source,
        now=NOW,
    )
    *_, repeated = pipeline(normalized_result=normalization)
    assert attr(repeated, "voltage").reason_codes == (
        SelectionReasonCode.INSUFFICIENT_CORROBORATION,
    )

    for values in (("415", "440"), ("415", "415", "440")):
        *_, conflicted = pipeline(*(("voltage", value, "V") for value in values))
        voltage = attr(conflicted, "voltage")
        assert voltage.selection_status is AttributeSelectionStatus.REVIEW_REQUIRED
        assert voltage.proposed_value is None and len(voltage.review_candidate_ids) == len(values)
        assert voltage.selection_confidence_bp == 0


def test_invalid_warning_missing_and_optional_policy() -> None:
    *_, mixed = pipeline(("efficiency", "92", "%"), ("efficiency", "105", "%"))
    efficiency = attr(mixed, "efficiency")
    assert efficiency.selection_status is AttributeSelectionStatus.REVIEW_REQUIRED
    assert efficiency.reason_codes == (SelectionReasonCode.VALUE_CONFLICT,)

    *_, unsupported = pipeline(("voltage", "415", "V"), ("voltage", "415", "rpm"))
    assert attr(unsupported, "voltage").selection_status is AttributeSelectionStatus.REVIEW_REQUIRED

    *_, invalid_only = pipeline(("voltage", "bad", "V"))
    invalid_voltage = attr(invalid_only, "voltage")
    assert invalid_voltage.selection_status is AttributeSelectionStatus.NO_VALID_CANDIDATE
    assert invalid_voltage.review_required

    *_, sparse = pipeline(("ratedPower", "5.5", "kW"), ("ratedPower", "5.5", "kW"))
    assert attr(sparse, "phase").selection_status is AttributeSelectionStatus.NO_CANDIDATE
    assert attr(sparse, "phase").review_required
    assert attr(sparse, "ipRating").selection_status is AttributeSelectionStatus.NO_CANDIDATE
    assert not attr(sparse, "ipRating").review_required
    assert sparse.overall_status is ProductReviewStatus.INSUFFICIENT_DATA


def test_all_required_auto_selected_is_ready_for_auto_approval() -> None:
    required = (
        ("ratedPower", "5.5", "kW"),
        ("voltage", "415", "V"),
        ("frequency", "50", "Hz"),
        ("speedRpm", "1440", "rpm"),
        ("phase", "3", None),
    )
    items = tuple(value for pair in ((item, item) for item in required) for value in pair)
    *_, result = pipeline(*items)
    assert result.overall_status is ProductReviewStatus.READY_FOR_AUTO_APPROVAL
    assert result.required_auto_selected_count == result.review_summary.required_attribute_count


def test_lineage_mismatch_is_rejected() -> None:
    _, normalization, conflict, validation, completeness, _ = pipeline(("voltage", "415", "V"))
    with pytest.raises(AttributeSelectionLineageMismatchError):
        AttributeSelectionEngine().select(
            job_id=uuid4(),
            conflict_result=conflict,
            validation_result=replace(validation, extraction_id=uuid4()),
            completeness_result=completeness,
            normalization_result=normalization,
            now=NOW,
        )
