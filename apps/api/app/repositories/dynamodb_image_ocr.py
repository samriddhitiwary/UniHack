"""Composite DynamoDB repository for image OCR results."""

import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    ImageOcrRepositoryError,
    ImageOcrResultAlreadyExistsError,
    ImageOcrResultItemTooLargeError,
    ImageOcrSerializationError,
    ProductSerializationError,
)
from app.domain.image_ocr import ImageOcrResult
from app.utils.dynamodb import (
    AttributeValue,
    WireItem,
    deserialize_item,
    image_ocr_block_to_item,
    image_ocr_metadata_to_item,
    image_ocr_result_from_items,
    serialize_item,
)

JOB_ID_INDEX = "JobIdIndex"
MAX_SAFE_ITEM_BYTES = 390_000


class DynamoDBImageOcrResultRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client = client
        self._table_name = table_name

    def create(self, result: ImageOcrResult) -> ImageOcrResult:
        try:
            records = [image_ocr_metadata_to_item(result)] + [
                image_ocr_block_to_item(result.ocr_id, index, block)
                for index, block in enumerate(result.blocks, start=1)
            ]
            wire_records = [serialize_item(record) for record in records]
            if any(_wire_size(record) > MAX_SAFE_ITEM_BYTES for record in wire_records):
                raise ImageOcrResultItemTooLargeError()
            for index, record in enumerate(wire_records):
                attribute = "ocrId" if index == 0 else "recordKey"
                self._client.put_item(
                    TableName=self._table_name,
                    Item=record,
                    ConditionExpression=f"attribute_not_exists(#{attribute})",
                    ExpressionAttributeNames={f"#{attribute}": attribute},
                )
        except (ImageOcrResultItemTooLargeError, ImageOcrSerializationError):
            raise
        except ClientError as exc:
            if _error_code(exc) == "ConditionalCheckFailedException":
                raise ImageOcrResultAlreadyExistsError("OCR result already exists") from exc
            raise ImageOcrRepositoryError("OCR result could not be created") from exc
        except (BotoCoreError, ProductSerializationError) as exc:
            raise ImageOcrRepositoryError("OCR result could not be created") from exc
        return result

    def get_by_id(self, ocr_id: UUID) -> ImageOcrResult | None:
        items: list[Mapping[str, AttributeValue]] = []
        start_key: WireItem | None = None
        try:
            while True:
                request: dict[str, Any] = {
                    "TableName": self._table_name,
                    "KeyConditionExpression": "#ocrId = :ocrId",
                    "ExpressionAttributeNames": {"#ocrId": "ocrId"},
                    "ExpressionAttributeValues": serialize_item({":ocrId": ocr_id}),
                    "ConsistentRead": True,
                }
                if start_key is not None:
                    request["ExclusiveStartKey"] = start_key
                response = self._client.query(**request)
                items.extend(cast(list[Mapping[str, AttributeValue]], response.get("Items", [])))
                start_key = cast(WireItem | None, response.get("LastEvaluatedKey"))
                if not start_key:
                    break
            if not items:
                return None
            return _to_result(items)
        except ImageOcrRepositoryError:
            raise
        except (BotoCoreError, ClientError) as exc:
            raise ImageOcrRepositoryError("OCR result could not be retrieved") from exc

    def get_by_job_id(self, job_id: UUID) -> ImageOcrResult | None:
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
            return self.get_by_id(UUID(str(metadata["ocrId"])))
        except ImageOcrRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, TypeError, ValueError) as exc:
            raise ImageOcrRepositoryError("OCR result could not be retrieved for job") from exc


def _to_result(items: list[Mapping[str, AttributeValue]]) -> ImageOcrResult:
    try:
        return image_ocr_result_from_items([deserialize_item(item) for item in items])
    except ImageOcrSerializationError:
        raise
    except ProductSerializationError as exc:
        raise ImageOcrSerializationError("DynamoDB OCR records are invalid") from exc


def _wire_size(item: WireItem) -> int:
    return len(json.dumps(item, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))
