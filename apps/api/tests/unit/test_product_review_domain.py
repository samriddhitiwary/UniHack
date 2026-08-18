"""Product-review aggregate and immutable decision invariants."""

from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from uuid import uuid4

import pytest

from app.domain.product_review import (
    AttributeReviewDecision,
    AttributeReviewDecisionType,
    ProductReviewSession,
    ProductReviewSessionStatus,
)
from tests.fixtures.attribute_normalization import NOW
from tests.unit.test_attribute_selection_engine import pipeline


def test_review_creation_has_open_versioned_unresolved_state() -> None:
    *_, selection = pipeline(("voltage", "415", "V"))
    review = ProductReviewSession.create(selection, NOW)
    assert review.status is ProductReviewSessionStatus.OPEN
    assert review.version == 1 and review.decision_count == 0
    assert review.required_unresolved_count == review.required_attribute_count
    assert not review.completion_ready
    with pytest.raises(FrozenInstanceError):
        review.version = 2  # type: ignore[misc]


def test_decision_is_immutable_and_enforces_field_coherence() -> None:
    *_, selection = pipeline(("voltage", "415", "V"))
    review = ProductReviewSession.create(selection, NOW)
    decision = AttributeReviewDecision(
        decision_id=uuid4(),
        review_id=review.review_id,
        product_id=review.product_id,
        decision_sequence=1,
        attribute_name="voltage",
        decision_type=AttributeReviewDecisionType.MANUAL_OVERRIDE,
        candidate_id=None,
        approved_value="430",
        approved_unit="V",
        manual_raw_value="430",
        manual_raw_unit="V",
        comment=None,
        reviewer_id="reviewer-local-001",
        review_version=2,
        created_at=NOW,
    )
    assert decision.created_at.utcoffset() is not None
    with pytest.raises(FrozenInstanceError):
        decision.comment = "changed"  # type: ignore[misc]
    with pytest.raises(ValueError):
        replace(decision, decision_type=AttributeReviewDecisionType.REJECT_ALL)


def test_completion_requires_resolution_and_sets_utc_timestamp() -> None:
    *_, selection = pipeline(("voltage", "415", "V"))
    review = ProductReviewSession.create(selection, NOW)
    with pytest.raises(ValueError):
        review.complete(NOW)
    resolved = replace(
        review,
        required_resolved_count=review.required_attribute_count,
        required_unresolved_count=0,
    )
    completed = resolved.complete(NOW + timedelta(seconds=1))
    assert completed.status is ProductReviewSessionStatus.COMPLETED
    assert completed.version == 2 and completed.completed_at == NOW + timedelta(seconds=1)
