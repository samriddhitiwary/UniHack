"""Opt-in DynamoDB Local catalog export result persistence contract."""

import os

import pytest

from app.api.dependencies.dynamodb import create_dynamodb_client
from app.core.config import get_settings
from app.repositories.dynamodb_catalog_export import DynamoDBCatalogExportResultRepository
from app.utils.dynamodb import serialize_item
from tests.fixtures.catalog_export import export_result

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DYNAMODB_INTEGRATION") != "1",
    reason="set RUN_DYNAMODB_INTEGRATION=1 after creating catalog-export-results",
)


def test_catalog_export_repository_contract_against_dynamodb_local() -> None:
    settings = get_settings()
    client = create_dynamodb_client(settings)
    table_name = settings.table_name("catalog-export-results")
    repository = DynamoDBCatalogExportResultRepository(client, table_name)
    result = export_result()[3]
    try:
        assert repository.create(result) == result
        assert repository.get_by_id(result.export_id) == result
        assert repository.get_by_job_id(result.job_id) == result
        assert repository.get_by_projection_id(result.projection_id) == result
    finally:
        for partition_id in (result.export_id, f"PROJECTION#{result.projection_id}"):
            response = client.query(
                TableName=table_name,
                KeyConditionExpression="#id=:id",
                ExpressionAttributeNames={"#id": "exportId"},
                ExpressionAttributeValues=serialize_item({":id": partition_id}),
            )
            for item in response.get("Items", []):
                client.delete_item(
                    TableName=table_name,
                    Key={"exportId": item["exportId"], "recordKey": item["recordKey"]},
                )
