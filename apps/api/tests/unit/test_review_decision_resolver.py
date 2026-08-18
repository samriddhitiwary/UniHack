from dataclasses import replace
from uuid import uuid4

import pytest

from app.core.exceptions import ReviewedMaterializationReviewStateInvalidError
from app.domain.product_review import CurrentAttributeReviewDecision
from app.services.review_decision_resolver import ReviewDecisionResolver
from tests.fixtures.reviewed_attributes import completed_review


def test_resolves_current_latest_and_ignores_historical_decision() -> None:
    *_, decisions, current = completed_review()
    old = replace(decisions[0], decision_sequence=1)
    revised = replace(decisions[0], decision_id=uuid4(), decision_sequence=99)
    projection = CurrentAttributeReviewDecision.from_decision(revised)
    history = (old, *decisions[1:], revised)
    current_state = (projection, *current[1:])
    resolved = ReviewDecisionResolver().resolve(
        review_id=revised.review_id,
        product_id=revised.product_id,
        current=current_state,
        history=history,
    )
    assert resolved[revised.attribute_name] is revised


def test_rejects_missing_mismatched_or_duplicate_current_state() -> None:
    *_, decisions, current = completed_review()
    resolver = ReviewDecisionResolver()
    with pytest.raises(ReviewedMaterializationReviewStateInvalidError):
        resolver.resolve(
            review_id=decisions[0].review_id,
            product_id=decisions[0].product_id,
            current=(current[0], current[0]),
            history=decisions,
        )
    foreign = replace(decisions[0], review_id=uuid4())
    with pytest.raises(ReviewedMaterializationReviewStateInvalidError):
        resolver.resolve(
            review_id=decisions[0].review_id,
            product_id=decisions[0].product_id,
            current=current,
            history=(foreign, *decisions[1:]),
        )
    with pytest.raises(ReviewedMaterializationReviewStateInvalidError):
        resolver.resolve(
            review_id=decisions[0].review_id,
            product_id=decisions[0].product_id,
            current=(replace(current[0], decision_sequence=999),),
            history=decisions,
        )
