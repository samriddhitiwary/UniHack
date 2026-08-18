from dataclasses import FrozenInstanceError, replace
from uuid import uuid4

import pytest

from app.core.exceptions import (
    ReviewedMaterializationDecisionInvalidError,
    ReviewedMaterializationRequiredAttributeUnresolvedError,
    ReviewedMaterializationReviewNotCompletedError,
    ReviewedMaterializationUnknownAttributeError,
)
from app.domain.attribute_validation import CandidateValidationStatus
from app.domain.product_review import AttributeReviewDecisionType, ProductReviewSessionStatus
from app.domain.reviewed_attributes import FinalAttributeOrigin, ReviewedAttributeSetStatus
from app.services.reviewed_attribute_materialization_engine import (
    ReviewedAttributeMaterializationEngine,
)
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.reviewed_attributes import completed_pump_review, completed_review


def run(*, conflict=False, manual=False, warning=False, decisions=None, review_override=None):
    schema, normalization, _, validation, _, selection, review, default, _ = completed_review(
        conflict_voltage=conflict, manual_voltage=manual, warning_power=warning
    )
    return ReviewedAttributeMaterializationEngine().materialize(
        job_id=uuid4(),
        review=review_override or review,
        current_decisions=decisions or default,
        schema=schema,
        selection_result=selection,
        validation_result=validation,
        normalization_result=normalization,
        now=NOW,
    )


def test_materializes_proposed_candidates_in_schema_order_and_optional_absence() -> None:
    result = run()
    assert result.status is ReviewedAttributeSetStatus.MATERIALIZED
    assert result.materialized_required_count == result.required_attribute_count == 5
    assert result.unresolved_optional_count == result.optional_attribute_count
    assert all(a.origin is FinalAttributeOrigin.APPROVED_PROPOSED for a in result.attributes)
    assert [a.display_order for a in result.attributes] == sorted(
        a.display_order for a in result.attributes
    )
    assert all(a.candidate_id and a.source_candidate_id and a.source_id for a in result.attributes)


def test_materializes_conflict_choice_and_manual_override_lineage() -> None:
    candidate = run(conflict=True)
    voltage = next(a for a in candidate.attributes if a.attribute_name == "voltage")
    assert voltage.value == "440" and voltage.origin is FinalAttributeOrigin.APPROVED_CANDIDATE
    assert voltage.validation_status is not None
    manual = run(manual=True)
    voltage = next(a for a in manual.attributes if a.attribute_name == "voltage")
    assert voltage.value == "430" and voltage.origin is FinalAttributeOrigin.HUMAN_OVERRIDE
    assert voltage.candidate_id is None and voltage.manual_raw_value == "430"
    assert voltage.selection_confidence_bp is None


def test_open_review_required_missing_and_unknown_are_rejected() -> None:
    *_, review, decisions, _ = completed_review()
    with pytest.raises(ReviewedMaterializationReviewNotCompletedError):
        run(
            review_override=replace(
                review, status=ProductReviewSessionStatus.OPEN, completed_at=None
            )
        )
    with pytest.raises(ReviewedMaterializationRequiredAttributeUnresolvedError):
        run(decisions=decisions[1:])
    rejected = replace(
        decisions[0],
        decision_type=AttributeReviewDecisionType.REJECT_ALL,
        candidate_id=None,
        approved_value=None,
        approved_unit=None,
    )
    with pytest.raises(ReviewedMaterializationRequiredAttributeUnresolvedError):
        run(decisions=(rejected, *decisions[1:]))
    unknown = replace(decisions[0], attribute_name="unknownAttribute")
    with pytest.raises(ReviewedMaterializationUnknownAttributeError):
        run(decisions=(unknown, *decisions[1:]))


def test_result_and_attributes_are_immutable_and_counts_coherent() -> None:
    result = run()
    with pytest.raises(FrozenInstanceError):
        result.attribute_count = 0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.attributes[0].value = "changed"  # type: ignore[misc]
    with pytest.raises(ValueError):
        replace(result, materialized_required_count=4)


def test_preserves_warning_status_and_rejects_invalid_candidate_lineage() -> None:
    warning = run(warning=True)
    power = next(a for a in warning.attributes if a.attribute_name == "ratedPower")
    assert power.validation_status is CandidateValidationStatus.VALID_WITH_WARNINGS

    *_, decisions, _ = completed_review()
    wrong_origin = replace(
        decisions[0],
        decision_type=AttributeReviewDecisionType.APPROVE_CANDIDATE,
    )
    with pytest.raises(ReviewedMaterializationDecisionInvalidError):
        run(decisions=(wrong_origin, *decisions[1:]))


def test_materializes_required_pump_attributes() -> None:
    schema, normalization, _, validation, _, selection, review, decisions, _ = (
        completed_pump_review()
    )
    result = ReviewedAttributeMaterializationEngine().materialize(
        job_id=uuid4(),
        review=review,
        current_decisions=decisions,
        schema=schema,
        selection_result=selection,
        validation_result=validation,
        normalization_result=normalization,
        now=NOW,
    )
    assert {item.attribute_name for item in result.attributes} >= {"flowRate", "head"}
    assert result.materialized_required_count == result.required_attribute_count
