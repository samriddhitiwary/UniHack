"""Opt-in DynamoDB Local contract test for CSV processing-result persistence."""

import os

import pytest

from app.api.dependencies.dynamodb import create_dynamodb_client
from app.core.config import get_settings
from app.repositories.dynamodb_csv_processing import DynamoDBCsvProcessingResultRepository
from app.utils.dynamodb import serialize_item
from tests.fixtures.csv_processing import make_csv_processing_result

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DYNAMODB_INTEGRATION") != "1",
    reason="set RUN_DYNAMODB_INTEGRATION=1 after creating the csv-processing-results table",
)


def test_csv_processing_repository_contract_against_dynamodb_local() -> None:
    settings = get_settings()
    client = create_dynamodb_client(settings)
    table_name = settings.table_name("csv-processing-results")
    repository = DynamoDBCsvProcessingResultRepository(client, table_name)
    result = make_csv_processing_result()
    try:
        assert repository.create(result) == result
        assert repository.get_by_id(result.processing_id) == result
        assert repository.get_by_job_id(result.job_id) == result
    finally:
        response = client.query(
            TableName=table_name,
            KeyConditionExpression="#id = :id",
            ExpressionAttributeNames={"#id": "processingId"},
            ExpressionAttributeValues=serialize_item({":id": result.processing_id}),
            ProjectionExpression="processingId, recordKey",
        )
        for item in response.get("Items", []):
            client.delete_item(TableName=table_name, Key=item)
