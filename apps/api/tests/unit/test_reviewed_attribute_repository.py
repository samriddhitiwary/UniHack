from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError
from pydantic import ValidationError

from app.core.exceptions import (
    ReviewedAttributeRepositoryError,
    ReviewedAttributeSerializationError,
    ReviewedMaterializationAlreadyExistsError,
)
from app.repositories.dynamodb_reviewed_attributes import (
    JOB_ID_INDEX,
    REVIEW_ID_INDEX,
    DynamoDBFinalReviewedAttributeRepository,
)
from app.schemas.reviewed_attributes import FinalReviewedAttributeSetRecord
from app.services.review_decision_resolver import ReviewDecisionResolver
from app.services.reviewed_attribute_materialization_engine import (
    ReviewedAttributeMaterializationEngine,
)
from app.utils.dynamodb import serialize_item
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.reviewed_attributes import completed_review


def materialized_result():
    schema, normalization, _, validation, _, selection, review, decisions, current = (
        completed_review(manual_voltage=True)
    )
    resolved = ReviewDecisionResolver().resolve(
        review_id=review.review_id,
        product_id=review.product_id,
        current=current,
        history=decisions,
    )
    return ReviewedAttributeMaterializationEngine().materialize(
        job_id=review.review_id,
        review=review,
        current_decisions=tuple(resolved.values()),
        schema=schema,
        selection_result=selection,
        validation_result=validation,
        normalization_result=normalization,
        now=NOW,
    )


def conditional_error() -> ClientError:
    return ClientError(
        {"Error": {"Code": "TransactionCanceledException", "Message": "conditional"}},
        "TransactWriteItems",
    )


def test_create_uses_meta_review_guard_and_conditional_attribute_writes() -> None:
    client = MagicMock()
    repository = DynamoDBFinalReviewedAttributeRepository(client, "reviewed")
    result = materialized_result()
    assert repository.create(result) is result
    transaction = client.transact_write_items.call_args.kwargs["TransactItems"]
    assert len(transaction) == 2
    guard = transaction[1]["Put"]["Item"]
    assert guard["materializationId"]["S"] == f"REVIEW#{result.review_id}"
    assert "reviewId" not in guard and "createdAt" not in guard
    assert client.put_item.call_count == result.attribute_count
    client.transact_write_items.side_effect = conditional_error()
    with pytest.raises(ReviewedMaterializationAlreadyExistsError):
        repository.create(result)


def test_partial_attribute_write_is_reported_and_incomplete_partition_is_detected() -> None:
    client = MagicMock()
    repository = DynamoDBFinalReviewedAttributeRepository(client, "reviewed")
    result = materialized_result()
    client.put_item.side_effect = [
        None,
        ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": "busy"}},
            "PutItem",
        ),
    ]
    with pytest.raises(ReviewedAttributeRepositoryError):
        repository.create(result)
    client.query.return_value = {
        "Items": [
            serialize_item(repository._meta(result)),
            serialize_item(
                repository._attribute(result.materialization_id, 1, result.attributes[0])
            ),
        ]
    }
    with pytest.raises(ReviewedAttributeSerializationError):
        repository.get_by_id(result.materialization_id)


def test_meta_and_attribute_records_round_trip_and_detect_missing_records() -> None:
    client = MagicMock()
    repository = DynamoDBFinalReviewedAttributeRepository(client, "reviewed")
    result = materialized_result()
    items = [
        serialize_item(repository._meta(result)),
        *(
            serialize_item(repository._attribute(result.materialization_id, i, value))
            for i, value in enumerate(result.attributes, 1)
        ),
    ]
    client.query.return_value = {"Items": items}
    assert repository.get_by_id(result.materialization_id) == result
    client.query.return_value = {"Items": items[:-1]}
    with pytest.raises(ReviewedAttributeSerializationError):
        repository.get_by_id(result.materialization_id)
    client.scan.assert_not_called()


def test_internal_schema_round_trip_uses_camel_case_and_rejects_extra_fields() -> None:
    result = materialized_result()
    record = FinalReviewedAttributeSetRecord.model_validate(result)
    payload = record.model_dump()
    assert payload["materializationId"] == result.materialization_id
    assert payload["attributes"][0]["reviewDecisionId"]
    with pytest.raises(ValidationError):
        FinalReviewedAttributeSetRecord.model_validate({**payload, "unexpected": True})


@pytest.mark.parametrize(
    ("method", "index", "key", "value_name"),
    [
        ("get_by_job_id", JOB_ID_INDEX, "jobId", "job_id"),
        ("get_by_review_id", REVIEW_ID_INDEX, "reviewId", "review_id"),
    ],
)
def test_sparse_index_lookup_resolves_full_artifact(method, index, key, value_name) -> None:
    client = MagicMock()
    repository = DynamoDBFinalReviewedAttributeRepository(client, "reviewed")
    result = materialized_result()
    meta = serialize_item(repository._meta(result))
    attributes = [
        serialize_item(repository._attribute(result.materialization_id, i, value))
        for i, value in enumerate(result.attributes, 1)
    ]
    client.query.side_effect = [{"Items": [meta]}, {"Items": [meta, *attributes]}]
    assert getattr(repository, method)(getattr(result, value_name)) == result
    first = client.query.call_args_list[0].kwargs
    assert first["IndexName"] == index
    assert first["ExpressionAttributeNames"] == {"#key": key}
    client.scan.assert_not_called()
