"""Composite DynamoDB persistence for product-classification results."""

import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    ProductClassificationRepositoryError,
    ProductClassificationResultAlreadyExistsError,
    ProductClassificationResultItemTooLargeError,
)
from app.domain.product_classification import ProductClassificationResult
from app.utils.dynamodb import (
    AttributeValue,
    WireItem,
    deserialize_item,
    product_classification_match_to_item,
    product_classification_metadata_to_item,
    product_classification_result_from_items,
    serialize_item,
)

JOB_ID_INDEX = "JobIdIndex"
MAX_SAFE_ITEM_BYTES = 390_000


class DynamoDBProductClassificationResultRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client = client
        self._table_name = table_name

    def create(self, result: ProductClassificationResult) -> ProductClassificationResult:
        records = [product_classification_metadata_to_item(result)] + [
            product_classification_match_to_item(result.classification_id, index, match)
            for index, match in enumerate(result.matches, start=1)
        ]
        wire = [serialize_item(record) for record in records]
        if any(
            len(json.dumps(item, separators=(",", ":"), default=str).encode()) > MAX_SAFE_ITEM_BYTES
            for item in wire
        ):
            raise ProductClassificationResultItemTooLargeError()
        try:
            for index, item in enumerate(wire):
                attribute = "classificationId" if index == 0 else "recordKey"
                self._client.put_item(
                    TableName=self._table_name,
                    Item=item,
                    ConditionExpression=f"attribute_not_exists(#{attribute})",
                    ExpressionAttributeNames={f"#{attribute}": attribute},
                )
        except ClientError as exc:
            if (
                str(exc.response.get("Error", {}).get("Code", ""))
                == "ConditionalCheckFailedException"
            ):
                raise ProductClassificationResultAlreadyExistsError(
                    "classification result already exists"
                ) from exc
            raise ProductClassificationRepositoryError(
                "classification result could not be created"
            ) from exc
        except BotoCoreError as exc:
            raise ProductClassificationRepositoryError(
                "classification result could not be created"
            ) from exc
        return result

    def get_by_id(self, classification_id: UUID) -> ProductClassificationResult | None:
        items: list[Mapping[str, AttributeValue]] = []
        start_key: WireItem | None = None
        try:
            while True:
                request: dict[str, Any] = {
                    "TableName": self._table_name,
                    "KeyConditionExpression": "#classificationId = :classificationId",
                    "ExpressionAttributeNames": {"#classificationId": "classificationId"},
                    "ExpressionAttributeValues": serialize_item(
                        {":classificationId": classification_id}
                    ),
                    "ConsistentRead": True,
                }
                if start_key:
                    request["ExclusiveStartKey"] = start_key
                response = self._client.query(**request)
                items.extend(cast(list[Mapping[str, AttributeValue]], response.get("Items", [])))
                start_key = cast(WireItem | None, response.get("LastEvaluatedKey"))
                if not start_key:
                    break
            return (
                product_classification_result_from_items([deserialize_item(item) for item in items])
                if items
                else None
            )
        except ProductClassificationRepositoryError:
            raise
        except (BotoCoreError, ClientError) as exc:
            raise ProductClassificationRepositoryError(
                "classification result could not be retrieved"
            ) from exc

    def get_by_job_id(self, job_id: UUID) -> ProductClassificationResult | None:
        try:
            response = self._client.query(
                TableName=self._table_name,
                IndexName=JOB_ID_INDEX,
                KeyConditionExpression="#jobId = :jobId",
                ExpressionAttributeNames={"#jobId": "jobId"},
                ExpressionAttributeValues=serialize_item({":jobId": job_id}),
                ScanIndexForward=False,
                Limit=1,
            )
            items = cast(list[Mapping[str, AttributeValue]], response.get("Items", []))
            if not items:
                return None
            metadata = deserialize_item(items[0])
            return self.get_by_id(UUID(str(metadata["classificationId"])))
        except ProductClassificationRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, TypeError, ValueError) as exc:
            raise ProductClassificationRepositoryError(
                "classification result could not be retrieved for job"
            ) from exc
