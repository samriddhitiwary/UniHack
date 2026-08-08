"""Composite-item DynamoDB repository for PDF table-extraction results."""

import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    PdfTableExtractionRepositoryError,
    PdfTableExtractionResultAlreadyExistsError,
    PdfTableExtractionSerializationError,
    ProductSerializationError,
)
from app.domain.pdf_table_extraction import PdfTableExtractionResult
from app.utils.dynamodb import (
    AttributeValue,
    WireItem,
    deserialize_item,
    pdf_table_extraction_metadata_to_item,
    pdf_table_extraction_result_from_items,
    pdf_table_extraction_table_to_item,
    serialize_item,
)

JOB_ID_INDEX = "JobIdIndex"
MAX_SAFE_ITEM_BYTES = 390_000


class DynamoDBPdfTableExtractionRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client = client
        self._table_name = table_name

    def create(self, result: PdfTableExtractionResult) -> PdfTableExtractionResult:
        try:
            records = [pdf_table_extraction_metadata_to_item(result)] + [
                pdf_table_extraction_table_to_item(result.extraction_id, table)
                for table in result.tables
            ]
            wire_records = [serialize_item(record) for record in records]
            if any(_wire_size(record) > MAX_SAFE_ITEM_BYTES for record in wire_records):
                raise PdfTableExtractionSerializationError("table record exceeds safe item size")
            for index, record in enumerate(wire_records):
                attribute = "extractionId" if index == 0 else "recordKey"
                self._client.put_item(
                    TableName=self._table_name,
                    Item=record,
                    ConditionExpression=f"attribute_not_exists(#{attribute})",
                    ExpressionAttributeNames={f"#{attribute}": attribute},
                )
        except PdfTableExtractionSerializationError:
            raise
        except ClientError as exc:
            if _error_code(exc) == "ConditionalCheckFailedException":
                raise PdfTableExtractionResultAlreadyExistsError(
                    "PDF table-extraction result already exists"
                ) from exc
            raise PdfTableExtractionRepositoryError("table result could not be created") from exc
        except (BotoCoreError, ProductSerializationError) as exc:
            raise PdfTableExtractionRepositoryError("table result could not be created") from exc
        return result

    def get_by_id(self, extraction_id: UUID) -> PdfTableExtractionResult | None:
        items: list[Mapping[str, AttributeValue]] = []
        start_key: WireItem | None = None
        try:
            while True:
                request: dict[str, Any] = {
                    "TableName": self._table_name,
                    "KeyConditionExpression": "#extractionId = :extractionId",
                    "ExpressionAttributeNames": {"#extractionId": "extractionId"},
                    "ExpressionAttributeValues": serialize_item({":extractionId": extraction_id}),
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
        except PdfTableExtractionRepositoryError:
            raise
        except (BotoCoreError, ClientError) as exc:
            raise PdfTableExtractionRepositoryError("table result could not be retrieved") from exc

    def get_by_job_id(self, job_id: UUID) -> PdfTableExtractionResult | None:
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
            return self.get_by_id(UUID(str(metadata["extractionId"])))
        except PdfTableExtractionRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, TypeError, ValueError) as exc:
            raise PdfTableExtractionRepositoryError(
                "table result could not be retrieved for job"
            ) from exc


def _to_result(items: list[Mapping[str, AttributeValue]]) -> PdfTableExtractionResult:
    try:
        return pdf_table_extraction_result_from_items([deserialize_item(item) for item in items])
    except PdfTableExtractionSerializationError:
        raise
    except ProductSerializationError as exc:
        raise PdfTableExtractionSerializationError("DynamoDB table records are invalid") from exc


def _wire_size(item: WireItem) -> int:
    return len(json.dumps(item, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))
