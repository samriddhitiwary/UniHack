"""Opt-in DynamoDB Local commerce catalog projection persistence contract."""

import os

import pytest

from app.api.dependencies.dynamodb import create_dynamodb_client
from app.core.config import get_settings
from app.repositories.dynamodb_catalog_projection import (
    DynamoDBCommerceCatalogProjectionRepository,
)
from app.utils.dynamodb import serialize_item
from tests.fixtures.catalog_projection import projected_result

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DYNAMODB_INTEGRATION") != "1",
    reason="set RUN_DYNAMODB_INTEGRATION=1 after creating catalog-projection-results",
)


def test_catalog_projection_repository_contract_against_dynamodb_local() -> None:
    settings = get_settings()
    client = create_dynamodb_client(settings)
    table_name = settings.table_name("catalog-projection-results")
    repository = DynamoDBCommerceCatalogProjectionRepository(client, table_name)
    result = projected_result()[2]
    try:
        assert repository.create(result) == result
        assert repository.get_by_id(result.projection_id) == result
        assert repository.get_by_job_id(result.job_id) == result
        assert repository.get_by_materialization_id(result.materialization_id) == result
    finally:
        for partition_id in (result.projection_id, f"MATERIALIZATION#{result.materialization_id}"):
            response = client.query(
                TableName=table_name,
                KeyConditionExpression="#id=:id",
                ExpressionAttributeNames={"#id": "projectionId"},
                ExpressionAttributeValues=serialize_item({":id": partition_id}),
            )
            for item in response.get("Items", []):
                client.delete_item(
                    TableName=table_name,
                    Key={"projectionId": item["projectionId"], "recordKey": item["recordKey"]},
                )
