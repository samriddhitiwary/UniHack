"""Opt-in DynamoDB Local contract for image OCR result persistence."""

import os

import pytest

from app.api.dependencies.dynamodb import create_dynamodb_client
from app.core.config import get_settings
from app.repositories.dynamodb_image_ocr import DynamoDBImageOcrResultRepository
from app.utils.dynamodb import serialize_item
from tests.fixtures.image_ocr import make_image_ocr_result

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DYNAMODB_INTEGRATION") != "1",
    reason="set RUN_DYNAMODB_INTEGRATION=1 after creating the image-ocr-results table",
)


def test_image_ocr_repository_contract_against_dynamodb_local() -> None:
    settings = get_settings()
    client = create_dynamodb_client(settings)
    table_name = settings.table_name("image-ocr-results")
    repository = DynamoDBImageOcrResultRepository(client, table_name)
    result = make_image_ocr_result()
    try:
        assert repository.create(result) == result
        assert repository.get_by_id(result.ocr_id) == result
        assert repository.get_by_job_id(result.job_id) == result
    finally:
        response = client.query(
            TableName=table_name,
            KeyConditionExpression="#ocrId = :ocrId",
            ExpressionAttributeNames={"#ocrId": "ocrId"},
            ExpressionAttributeValues=serialize_item({":ocrId": result.ocr_id}),
        )
        for item in response.get("Items", []):
            client.delete_item(
                TableName=table_name,
                Key={"ocrId": item["ocrId"], "recordKey": item["recordKey"]},
            )
