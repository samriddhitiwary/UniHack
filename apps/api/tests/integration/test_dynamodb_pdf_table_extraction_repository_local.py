"""Opt-in DynamoDB Local contract test for PDF table-result persistence."""

import os

import pytest

from app.api.dependencies.dynamodb import create_dynamodb_client
from app.core.config import get_settings
from app.repositories.dynamodb_pdf_table_extraction import (
    DynamoDBPdfTableExtractionRepository,
)
from app.utils.dynamodb import serialize_item
from tests.fixtures.pdf_table_extraction import make_pdf_table_extraction_result

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DYNAMODB_INTEGRATION") != "1",
    reason="set RUN_DYNAMODB_INTEGRATION=1 after creating the table-extraction-results table",
)


def test_pdf_table_extraction_repository_contract_against_dynamodb_local() -> None:
    settings = get_settings()
    client = create_dynamodb_client(settings)
    table_name = settings.table_name("table-extraction-results")
    repository = DynamoDBPdfTableExtractionRepository(client, table_name)
    result = make_pdf_table_extraction_result()
    try:
        assert repository.create(result) == result
        assert repository.get_by_id(result.extraction_id) == result
        assert repository.get_by_job_id(result.job_id) == result
    finally:
        response = client.query(
            TableName=table_name,
            KeyConditionExpression="#id = :id",
            ExpressionAttributeNames={"#id": "extractionId"},
            ExpressionAttributeValues=serialize_item({":id": result.extraction_id}),
            ProjectionExpression="extractionId, recordKey",
        )
        for item in response.get("Items", []):
            client.delete_item(TableName=table_name, Key=item)
