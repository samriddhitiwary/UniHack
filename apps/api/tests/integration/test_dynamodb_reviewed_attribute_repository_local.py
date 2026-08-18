"""Opt-in DynamoDB Local reviewed-attribute persistence contract."""

import os

import pytest

from app.api.dependencies.dynamodb import create_dynamodb_client
from app.core.config import get_settings
from app.repositories.dynamodb_reviewed_attributes import (
    DynamoDBFinalReviewedAttributeRepository,
)
from app.utils.dynamodb import serialize_item
from tests.unit.test_reviewed_attribute_repository import materialized_result

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DYNAMODB_INTEGRATION") != "1",
    reason="set RUN_DYNAMODB_INTEGRATION=1 after creating reviewed-attribute-results",
)


def test_reviewed_attribute_repository_contract_against_dynamodb_local() -> None:
    settings = get_settings()
    client = create_dynamodb_client(settings)
    table_name = settings.table_name("reviewed-attribute-results")
    repository = DynamoDBFinalReviewedAttributeRepository(client, table_name)
    result = materialized_result()
    try:
        assert repository.create(result) == result
        assert repository.get_by_id(result.materialization_id) == result
        assert repository.get_by_job_id(result.job_id) == result
        assert repository.get_by_review_id(result.review_id) == result
    finally:
        for partition_id in (result.materialization_id, f"REVIEW#{result.review_id}"):
            response = client.query(
                TableName=table_name,
                KeyConditionExpression="#id=:id",
                ExpressionAttributeNames={"#id": "materializationId"},
                ExpressionAttributeValues=serialize_item({":id": partition_id}),
            )
            for item in response.get("Items", []):
                client.delete_item(
                    TableName=table_name,
                    Key={
                        "materializationId": item["materializationId"],
                        "recordKey": item["recordKey"],
                    },
                )
