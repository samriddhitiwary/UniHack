"""Opt-in DynamoDB Local classification-result persistence contract."""

import os

import pytest

from app.api.dependencies.dynamodb import create_dynamodb_client
from app.core.config import get_settings
from app.repositories.dynamodb_product_classification import (
    DynamoDBProductClassificationResultRepository,
)
from app.utils.dynamodb import serialize_item
from tests.unit.test_product_classification_serialization import make_result

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DYNAMODB_INTEGRATION") != "1",
    reason="set RUN_DYNAMODB_INTEGRATION=1 after creating product-classification-results",
)


def test_classification_repository_contract_against_dynamodb_local() -> None:
    settings = get_settings()
    client = create_dynamodb_client(settings)
    table_name = settings.table_name("product-classification-results")
    repository = DynamoDBProductClassificationResultRepository(client, table_name)
    result = make_result()
    try:
        assert repository.create(result) == result
        assert repository.get_by_id(result.classification_id) == result
        assert repository.get_by_job_id(result.job_id) == result
    finally:
        response = client.query(
            TableName=table_name,
            KeyConditionExpression="#classificationId = :classificationId",
            ExpressionAttributeNames={"#classificationId": "classificationId"},
            ExpressionAttributeValues=serialize_item(
                {":classificationId": result.classification_id}
            ),
        )
        for item in response.get("Items", []):
            client.delete_item(
                TableName=table_name,
                Key={
                    "classificationId": item["classificationId"],
                    "recordKey": item["recordKey"],
                },
            )
