"""Composite-item DynamoDB repository for PDF extraction results."""

import logging
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    PdfExtractionRepositoryError,
    PdfExtractionResultAlreadyExistsError,
    PdfExtractionSerializationError,
    ProductSerializationError,
)
from app.domain.pdf_extraction import PdfTextExtractionResult
from app.utils.dynamodb import (
    AttributeValue,
    WireItem,
    deserialize_item,
    pdf_extraction_metadata_to_item,
    pdf_extraction_page_to_item,
    pdf_extraction_result_from_items,
    serialize_item,
)

JOB_ID_INDEX = "JobIdIndex"
logger = logging.getLogger(__name__)


class DynamoDBPdfExtractionResultRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client = client
        self._table_name = table_name

    def create(self, result: PdfTextExtractionResult) -> PdfTextExtractionResult:
        try:
            self._client.put_item(
                TableName=self._table_name,
                Item=serialize_item(pdf_extraction_metadata_to_item(result)),
                ConditionExpression="attribute_not_exists(#extractionId)",
                ExpressionAttributeNames={"#extractionId": "extractionId"},
            )
            for page in result.pages:
                self._client.put_item(
                    TableName=self._table_name,
                    Item=serialize_item(pdf_extraction_page_to_item(result.extraction_id, page)),
                    ConditionExpression="attribute_not_exists(#recordKey)",
                    ExpressionAttributeNames={"#recordKey": "recordKey"},
                )
        except ClientError as exc:
            if _error_code(exc) == "ConditionalCheckFailedException":
                raise PdfExtractionResultAlreadyExistsError(
                    "PDF extraction result already exists"
                ) from exc
            raise PdfExtractionRepositoryError(
                "PDF extraction result could not be created"
            ) from exc
        except (BotoCoreError, ProductSerializationError) as exc:
            raise PdfExtractionRepositoryError(
                "PDF extraction result could not be created"
            ) from exc
        logger.info(
            "event=pdf_text_extraction.result_created extraction_id=%s job_id=%s "
            "page_count=%s quality_status=%s",
            result.extraction_id,
            result.job_id,
            result.page_count,
            result.quality_status.value,
        )
        return result

    def get_by_id(self, extraction_id: UUID) -> PdfTextExtractionResult | None:
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
            result = _to_result(items)
        except PdfExtractionRepositoryError:
            raise
        except (BotoCoreError, ClientError) as exc:
            raise PdfExtractionRepositoryError(
                "PDF extraction result could not be retrieved"
            ) from exc
        logger.info(
            "event=pdf_text_extraction.result_retrieved extraction_id=%s job_id=%s",
            result.extraction_id,
            result.job_id,
        )
        return result

    def get_by_job_id(self, job_id: UUID) -> PdfTextExtractionResult | None:
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
            raw_items = cast(list[Mapping[str, AttributeValue]], response.get("Items", []))
            if not raw_items:
                return None
            metadata = deserialize_item(raw_items[0])
            extraction_id = UUID(str(metadata["extractionId"]))
            return self.get_by_id(extraction_id)
        except PdfExtractionRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, TypeError, ValueError) as exc:
            raise PdfExtractionRepositoryError(
                "PDF extraction result could not be retrieved for job"
            ) from exc


def _to_result(items: list[Mapping[str, AttributeValue]]) -> PdfTextExtractionResult:
    try:
        return pdf_extraction_result_from_items([deserialize_item(item) for item in items])
    except PdfExtractionSerializationError:
        raise
    except ProductSerializationError as exc:
        raise PdfExtractionSerializationError("DynamoDB extraction records are invalid") from exc


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))
