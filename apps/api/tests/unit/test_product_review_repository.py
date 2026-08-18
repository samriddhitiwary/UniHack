"""Transactional review repository, serialization, cursor, and integrity tests."""

from dataclasses import replace
from datetime import timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from app.core.exceptions import (
    ProductReviewAlreadyCompletedError,
    ProductReviewAlreadyExistsError,
    ProductReviewSerializationError,
)
from app.domain.product_review import (
    AttributeReviewDecision,
    AttributeReviewDecisionType,
    CurrentAttributeReviewDecision,
    ProductReviewSession,
)
from app.repositories.dynamodb_product_review import DynamoDBProductReviewRepository
from app.utils.dynamodb import serialize_item
from tests.fixtures.attribute_normalization import NOW
from tests.unit.test_attribute_selection_engine import pipeline


def review_and_decision():
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
        comment="confirmed",
        reviewer_id="reviewer-local-001",
        review_version=2,
        created_at=NOW,
    )
    updated = review.after_decision(required_resolved=1, optional_resolved=0, now=NOW)
    return review, updated, decision, CurrentAttributeReviewDecision.from_decision(decision)


def conditional_error(operation: str = "TransactWriteItems") -> ClientError:
    return ClientError(
        {"Error": {"Code": "TransactionCanceledException", "Message": "conditional"}},
        operation,
    )


def test_create_uses_atomic_meta_and_selection_uniqueness_guard() -> None:
    client = MagicMock()
    repository = DynamoDBProductReviewRepository(client, "reviews")
    review, *_ = review_and_decision()
    assert repository.create(review) is review
    transaction = client.transact_write_items.call_args.kwargs["TransactItems"]
    assert len(transaction) == 2
    assert transaction[0]["Put"]["ConditionExpression"] == "attribute_not_exists(#pk)"
    assert transaction[1]["Put"]["Item"]["reviewId"]["S"].startswith("SELECTION#")
    client.transact_write_items.side_effect = conditional_error()
    with pytest.raises(ProductReviewAlreadyExistsError):
        repository.create(review)


def test_meta_decision_and_current_round_trip_with_integrity_check() -> None:
    client = MagicMock()
    repository = DynamoDBProductReviewRepository(client, "reviews")
    review, _, decision, current = review_and_decision()
    items = [
        serialize_item(repository._meta(review)),
        serialize_item(repository._decision(decision)),
        serialize_item(repository._current(review.review_id, current)),
    ]
    client.query.return_value = {"Items": items}
    assert repository.get_by_id(review.review_id) == review
    client.query.return_value = {"Items": [items[0], items[2]]}
    with pytest.raises(ProductReviewSerializationError):
        repository.get_by_id(review.review_id)


def test_selection_guard_lookup_resolves_target_without_scan() -> None:
    client = MagicMock()
    repository = DynamoDBProductReviewRepository(client, "reviews")
    review, *_ = review_and_decision()
    client.get_item.return_value = {
        "Item": serialize_item(
            {
                "reviewId": f"SELECTION#{review.selection_id}",
                "recordKey": "REVIEW",
                "selectionId": review.selection_id,
                "targetReviewId": review.review_id,
            }
        )
    }
    client.query.return_value = {"Items": [serialize_item(repository._meta(review))]}
    assert repository.get_by_selection_id(review.selection_id) == review
    client.scan.assert_not_called()


def test_append_is_atomic_and_history_listing_is_chronological_and_paginated() -> None:
    client = MagicMock()
    repository = DynamoDBProductReviewRepository(client, "reviews")
    _, updated, decision, current = review_and_decision()
    assert repository.append_decision(updated, decision, current, expected_version=1) == updated
    transaction = client.transact_write_items.call_args.kwargs["TransactItems"]
    assert [next(iter(item)) for item in transaction] == ["Put", "Put", "Update"]
    assert transaction[2]["Update"]["ConditionExpression"] == (
        "#version=:expected AND #status=:open"
    )
    last_key = serialize_item({"reviewId": updated.review_id, "recordKey": "DECISION#000001"})
    client.query.return_value = {
        "Items": [serialize_item(repository._decision(decision))],
        "LastEvaluatedKey": last_key,
    }
    page = repository.list_decisions(updated.review_id, limit=50)
    assert page.items == (decision,) and page.next_cursor
    assert client.query.call_args.kwargs["ScanIndexForward"] is True
    client.scan.assert_not_called()


def test_current_projection_and_conditional_completion() -> None:
    client = MagicMock()
    repository = DynamoDBProductReviewRepository(client, "reviews")
    review, _, _, current = review_and_decision()
    client.query.return_value = {
        "Items": [serialize_item(repository._current(review.review_id, current))]
    }
    assert repository.list_current_decisions(review.review_id) == (current,)
    ready = replace(
        review,
        required_resolved_count=review.required_attribute_count,
        required_unresolved_count=0,
    )
    completed = ready.complete(NOW + timedelta(seconds=1))
    assert repository.complete(completed, expected_version=1) == completed
    assert client.update_item.call_args.kwargs["ConditionExpression"] == (
        "#version=:expected AND #status=:open"
    )


def test_completed_conditional_conflict_is_stable() -> None:
    client = MagicMock()
    repository = DynamoDBProductReviewRepository(client, "reviews")
    review, *_ = review_and_decision()
    completed = replace(
        review,
        required_resolved_count=review.required_attribute_count,
        required_unresolved_count=0,
    ).complete(NOW + timedelta(seconds=1))
    client.update_item.side_effect = ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "stale"}},
        "UpdateItem",
    )
    client.query.return_value = {"Items": [serialize_item(repository._meta(completed))]}
    with pytest.raises(ProductReviewAlreadyCompletedError):
        repository.complete(completed, expected_version=1)
