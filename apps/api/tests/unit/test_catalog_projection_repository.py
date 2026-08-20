from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.core.exceptions import (
    CatalogProjectionAlreadyExistsError,
    CatalogProjectionRepositoryError,
    CatalogProjectionSerializationError,
)
from app.repositories.dynamodb_catalog_projection import (
    JOB_ID_INDEX,
    MATERIALIZATION_ID_INDEX,
    PRODUCT_CREATED_AT_INDEX,
    DynamoDBCommerceCatalogProjectionRepository,
)
from app.utils.dynamodb import serialize_item
from tests.fixtures.catalog_projection import projected_result


def result_fixture():
    return projected_result(manual=True, clean=False)[2]


def conditional_error() -> ClientError:
    return ClientError(
        {"Error": {"Code": "TransactionCanceledException", "Message": "conditional"}},
        "TransactWriteItems",
    )


def test_create_uses_projection_and_materialization_guards() -> None:
    client = MagicMock()
    repository = DynamoDBCommerceCatalogProjectionRepository(client, "projections")
    result = result_fixture()
    assert repository.create(result) is result
    transaction = client.transact_write_items.call_args.kwargs["TransactItems"]
    assert len(transaction) == 2
    guard = transaction[1]["Put"]["Item"]
    assert guard["projectionId"]["S"] == f"MATERIALIZATION#{result.materialization_id}"
    assert "materializationId" not in guard and "createdAt" not in guard
    assert client.put_item.call_count == result.attribute_count
    client.transact_write_items.side_effect = conditional_error()
    with pytest.raises(CatalogProjectionAlreadyExistsError):
        repository.create(result)


def test_meta_attribute_round_trip_and_incomplete_partition_detection() -> None:
    client = MagicMock()
    repository = DynamoDBCommerceCatalogProjectionRepository(client, "projections")
    result = result_fixture()
    items = [
        serialize_item(repository._meta(result)),
        *(
            serialize_item(repository._attribute(result.projection_id, index, attribute))
            for index, attribute in enumerate(result.attributes, 1)
        ),
    ]
    client.query.return_value = {"Items": items}
    assert repository.get_by_id(result.projection_id) == result
    client.query.return_value = {"Items": items[:-1]}
    with pytest.raises(CatalogProjectionSerializationError):
        repository.get_by_id(result.projection_id)
    client.scan.assert_not_called()


@pytest.mark.parametrize(
    ("method", "index", "key", "field"),
    [
        ("get_by_job_id", JOB_ID_INDEX, "jobId", "job_id"),
        (
            "get_by_materialization_id",
            MATERIALIZATION_ID_INDEX,
            "materializationId",
            "materialization_id",
        ),
        ("get_latest_by_product_id", PRODUCT_CREATED_AT_INDEX, "productId", "product_id"),
    ],
)
def test_sparse_index_lookup_loads_full_partition(method, index, key, field) -> None:
    client = MagicMock()
    repository = DynamoDBCommerceCatalogProjectionRepository(client, "projections")
    result = result_fixture()
    meta = serialize_item(repository._meta(result))
    attributes = [
        serialize_item(repository._attribute(result.projection_id, i, attribute))
        for i, attribute in enumerate(result.attributes, 1)
    ]
    client.query.side_effect = [{"Items": [meta]}, {"Items": [meta, *attributes]}]
    assert getattr(repository, method)(getattr(result, field)) == result
    request = client.query.call_args_list[0].kwargs
    assert request["IndexName"] == index
    assert request["ExpressionAttributeNames"] == {"#key": key}
    client.scan.assert_not_called()


def test_partial_write_wraps_repository_failure_and_is_detectable() -> None:
    client = MagicMock()
    repository = DynamoDBCommerceCatalogProjectionRepository(client, "projections")
    result = result_fixture()
    client.put_item.side_effect = [
        None,
        ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": "busy"}},
            "PutItem",
        ),
    ]
    with pytest.raises(CatalogProjectionRepositoryError):
        repository.create(result)
    client.query.return_value = {
        "Items": [
            serialize_item(repository._meta(result)),
            serialize_item(repository._attribute(result.projection_id, 1, result.attributes[0])),
        ]
    }
    with pytest.raises(CatalogProjectionSerializationError):
        repository.get_by_id(result.projection_id)
