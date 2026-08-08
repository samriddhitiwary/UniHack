"""Composite-item DynamoDB repository for CSV processing results."""

import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    CsvProcessingRepositoryError,
    CsvProcessingResultAlreadyExistsError,
    CsvProcessingSerializationError,
    CsvResultItemTooLargeError,
    ProductSerializationError,
)
from app.domain.csv_processing import CsvProcessingResult
from app.utils.dynamodb import (
    AttributeValue,
    WireItem,
    csv_processing_metadata_to_item,
    csv_processing_result_from_items,
    csv_processing_row_to_item,
    deserialize_item,
    serialize_item,
)

JOB_ID_INDEX = "JobIdIndex"
MAX_SAFE_ITEM_BYTES = 390_000


class DynamoDBCsvProcessingResultRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client = client
        self._table_name = table_name

    def create(self, result: CsvProcessingResult) -> CsvProcessingResult:
        try:
            records = [csv_processing_metadata_to_item(result)] + [
                csv_processing_row_to_item(result.processing_id, row) for row in result.rows
            ]
            wire_records = [serialize_item(record) for record in records]
            if any(_wire_size(record) > MAX_SAFE_ITEM_BYTES for record in wire_records):
                raise CsvResultItemTooLargeError()
            for index, record in enumerate(wire_records):
                attribute = "processingId" if index == 0 else "recordKey"
                self._client.put_item(
                    TableName=self._table_name,
                    Item=record,
                    ConditionExpression=f"attribute_not_exists(#{attribute})",
                    ExpressionAttributeNames={f"#{attribute}": attribute},
                )
        except CsvResultItemTooLargeError:
            raise
        except ClientError as exc:
            if _error_code(exc) == "ConditionalCheckFailedException":
                raise CsvProcessingResultAlreadyExistsError(
                    "CSV processing result already exists"
                ) from exc
            raise CsvProcessingRepositoryError("CSV result could not be created") from exc
        except (BotoCoreError, ProductSerializationError) as exc:
            raise CsvProcessingRepositoryError("CSV result could not be created") from exc
        return result

    def get_by_id(self, processing_id: UUID) -> CsvProcessingResult | None:
        items: list[Mapping[str, AttributeValue]] = []
        start_key: WireItem | None = None
        try:
            while True:
                request: dict[str, Any] = {
                    "TableName": self._table_name,
                    "KeyConditionExpression": "#processingId = :processingId",
                    "ExpressionAttributeNames": {"#processingId": "processingId"},
                    "ExpressionAttributeValues": serialize_item({":processingId": processing_id}),
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
        except CsvProcessingRepositoryError:
            raise
        except (BotoCoreError, ClientError) as exc:
            raise CsvProcessingRepositoryError("CSV result could not be retrieved") from exc

    def get_by_job_id(self, job_id: UUID) -> CsvProcessingResult | None:
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
            return self.get_by_id(UUID(str(metadata["processingId"])))
        except CsvProcessingRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, TypeError, ValueError) as exc:
            raise CsvProcessingRepositoryError("CSV result could not be retrieved for job") from exc


def _to_result(items: list[Mapping[str, AttributeValue]]) -> CsvProcessingResult:
    try:
        return csv_processing_result_from_items([deserialize_item(item) for item in items])
    except CsvProcessingSerializationError:
        raise
    except ProductSerializationError as exc:
        raise CsvProcessingSerializationError("DynamoDB CSV records are invalid") from exc


def _wire_size(item: WireItem) -> int:
    return len(json.dumps(item, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))
