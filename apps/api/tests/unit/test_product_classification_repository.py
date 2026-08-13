"""DynamoDB product-classification result repository tests."""

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.core.exceptions import (
    ProductClassificationRepositoryError,
    ProductClassificationResultAlreadyExistsError,
)
from app.repositories.dynamodb_product_classification import (
    DynamoDBProductClassificationResultRepository,
)
from app.utils.dynamodb import (
    product_classification_match_to_item,
    product_classification_metadata_to_item,
    serialize_item,
)
from tests.unit.test_product_classification_serialization import make_result


def test_create_writes_meta_then_ordered_matches_conditionally() -> None:
    result = make_result()
    client = MagicMock()
    repository = DynamoDBProductClassificationResultRepository(client, "classifications")
    assert repository.create(result) == result
    assert client.put_item.call_count == len(result.matches) + 1
    assert client.put_item.call_args_list[0].kwargs["Item"]["recordKey"] == {"S": "META"}
    assert client.put_item.call_args_list[1].kwargs["Item"]["recordKey"] == {"S": "MATCH#000001"}


def test_duplicate_and_storage_failures_are_controlled() -> None:
    result = make_result()
    client = MagicMock()
    client.put_item.side_effect = ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem"
    )
    repository = DynamoDBProductClassificationResultRepository(client, "classifications")
    with pytest.raises(ProductClassificationResultAlreadyExistsError):
        repository.create(result)
    client.put_item.side_effect = ClientError({"Error": {"Code": "Internal"}}, "PutItem")
    with pytest.raises(ProductClassificationRepositoryError):
        repository.create(result)


def test_get_by_id_paginates_and_get_by_job_uses_sparse_index() -> None:
    result = make_result()
    metadata = serialize_item(product_classification_metadata_to_item(result))
    matches = [
        serialize_item(product_classification_match_to_item(result.classification_id, i, match))
        for i, match in enumerate(result.matches, start=1)
    ]
    client = MagicMock()
    client.query.side_effect = [
        {"Items": [metadata], "LastEvaluatedKey": {"k": {"S": "next"}}},
        {"Items": matches},
    ]
    repository = DynamoDBProductClassificationResultRepository(client, "classifications")
    assert repository.get_by_id(result.classification_id) == result
    client.query.side_effect = [{"Items": [metadata]}, {"Items": [metadata, *matches]}]
    assert repository.get_by_job_id(result.job_id) == result
    assert client.query.call_args_list[-2].kwargs["IndexName"] == "JobIdIndex"


def test_missing_results_return_none() -> None:
    client = MagicMock()
    client.query.return_value = {"Items": []}
    repository = DynamoDBProductClassificationResultRepository(client, "classifications")
    assert repository.get_by_id(make_result().classification_id) is None
    assert repository.get_by_job_id(make_result().job_id) is None
