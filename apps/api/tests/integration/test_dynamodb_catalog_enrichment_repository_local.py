"""Opt-in DynamoDB Local catalog enrichment persistence contract."""

import os

import pytest

from app.api.dependencies.dynamodb import create_dynamodb_client
from app.core.config import get_settings
from app.repositories.dynamodb_catalog_enrichment import (
    DynamoDBCatalogEnrichmentResultRepository,
    enrichment_input_hash,
)
from app.utils.dynamodb import serialize_item
from tests.unit.test_catalog_enrichment_repository import fixture_result

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DYNAMODB_INTEGRATION") != "1",
    reason="set RUN_DYNAMODB_INTEGRATION=1 after creating catalog-enrichment-results",
)


def test_catalog_enrichment_repository_contract_against_dynamodb_local() -> None:
    settings = get_settings()
    client = create_dynamodb_client(settings)
    table_name = settings.table_name("catalog-enrichment-results")
    repository = DynamoDBCatalogEnrichmentResultRepository(client, table_name)
    result = fixture_result()
    guard = enrichment_input_hash(
        projection_id=result.projection_id,
        prompt_version=result.prompt_version,
        provider=result.provider,
        model=result.model,
    )
    try:
        assert repository.create(result) == result
        assert repository.get_by_id(result.enrichment_id) == result
        assert repository.get_by_job_id(result.job_id) == result
        assert repository.get_by_projection_id(result.projection_id) == (result,)
    finally:
        for partition_id in (result.enrichment_id, f"ENRICHMENT_INPUT#{guard}"):
            response = client.query(
                TableName=table_name,
                KeyConditionExpression="#id=:id",
                ExpressionAttributeNames={"#id": "enrichmentId"},
                ExpressionAttributeValues=serialize_item({":id": partition_id}),
            )
            for item in response.get("Items", []):
                client.delete_item(
                    TableName=table_name,
                    Key={"enrichmentId": item["enrichmentId"], "recordKey": item["recordKey"]},
                )
