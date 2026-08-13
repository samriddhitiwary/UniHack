"""Composite DynamoDB persistence for structured attribute extraction results."""

import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    StructuredAttributeExtractionRepositoryError,
    StructuredAttributeExtractionResultAlreadyExistsError,
    StructuredAttributeExtractionResultItemTooLargeError,
    StructuredAttributeExtractionSerializationError,
)
from app.domain.attribute_extraction import (
    AttributeCandidate,
    AttributeExtractionEvidenceType,
    AttributeMatchType,
    AttributeValueParseStatus,
    StructuredAttributeExtractionResult,
    StructuredAttributeExtractionStatus,
)
from app.domain.category_schemas import AttributeDataType
from app.domain.products import ProductCategory
from app.utils.dynamodb import (
    AttributeValue,
    WireItem,
    deserialize_item,
    parse_utc,
    serialize_item,
)

JOB_ID_INDEX = "JobIdIndex"
MAX_SAFE_ITEM_BYTES = 390_000


class DynamoDBStructuredAttributeExtractionResultRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client, self._table_name = client, table_name

    def create(
        self, result: StructuredAttributeExtractionResult
    ) -> StructuredAttributeExtractionResult:
        records = [self._metadata(result)] + [
            self._candidate(result.extraction_id, index, candidate)
            for index, candidate in enumerate(result.candidates, 1)
        ]
        wire = [serialize_item(item) for item in records]
        if any(
            len(json.dumps(item, separators=(",", ":"), default=str).encode()) > MAX_SAFE_ITEM_BYTES
            for item in wire
        ):
            raise StructuredAttributeExtractionResultItemTooLargeError()
        try:
            for item in wire:
                self._client.put_item(
                    TableName=self._table_name,
                    Item=item,
                    ConditionExpression="attribute_not_exists(#recordKey)",
                    ExpressionAttributeNames={"#recordKey": "recordKey"},
                )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                raise StructuredAttributeExtractionResultAlreadyExistsError() from exc
            raise StructuredAttributeExtractionRepositoryError() from exc
        except BotoCoreError as exc:
            raise StructuredAttributeExtractionRepositoryError() from exc
        return result

    def get_by_id(self, extraction_id: UUID) -> StructuredAttributeExtractionResult | None:
        items: list[Mapping[str, AttributeValue]] = []
        start: WireItem | None = None
        try:
            while True:
                request: dict[str, Any] = {
                    "TableName": self._table_name,
                    "KeyConditionExpression": "#extractionId = :extractionId",
                    "ExpressionAttributeNames": {"#extractionId": "extractionId"},
                    "ExpressionAttributeValues": serialize_item({":extractionId": extraction_id}),
                    "ConsistentRead": True,
                }
                if start:
                    request["ExclusiveStartKey"] = start
                response = self._client.query(**request)
                items.extend(cast(list[Mapping[str, AttributeValue]], response.get("Items", [])))
                start = cast(WireItem | None, response.get("LastEvaluatedKey"))
                if not start:
                    break
            return self._from_items([deserialize_item(item) for item in items]) if items else None
        except StructuredAttributeExtractionRepositoryError:
            raise
        except (BotoCoreError, ClientError, ValueError, KeyError, TypeError) as exc:
            raise StructuredAttributeExtractionRepositoryError() from exc

    def get_by_job_id(self, job_id: UUID) -> StructuredAttributeExtractionResult | None:
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
            items = response.get("Items", [])
            return (
                None
                if not items
                else self.get_by_id(UUID(str(deserialize_item(items[0])["extractionId"])))
            )
        except StructuredAttributeExtractionRepositoryError:
            raise
        except (BotoCoreError, ClientError, ValueError, KeyError, TypeError) as exc:
            raise StructuredAttributeExtractionRepositoryError() from exc

    @staticmethod
    def _metadata(result: StructuredAttributeExtractionResult) -> dict[str, Any]:
        return {
            "extractionId": result.extraction_id,
            "recordKey": "META",
            "jobId": result.job_id,
            "productId": result.product_id,
            "classificationId": result.classification_id,
            "category": result.category,
            "schemaVersion": result.schema_version,
            "schemaFingerprint": result.schema_fingerprint,
            "status": result.status,
            "evidenceItemCount": result.evidence_item_count,
            "candidateCount": result.candidate_count,
            "distinctAttributeCount": result.distinct_attribute_count,
            "duplicateCount": result.duplicate_count,
            "warningCodes": list(result.warning_codes),
            "engine": result.engine,
            "engineVersion": result.engine_version,
            "createdAt": result.created_at,
        }

    @staticmethod
    def _candidate(extraction_id: UUID, index: int, value: AttributeCandidate) -> dict[str, Any]:
        return {
            "extractionId": extraction_id,
            "recordKey": f"CANDIDATE#{index:06d}",
            "candidateId": value.candidate_id,
            "attributeName": value.attribute_name,
            "attributeDisplayName": value.attribute_display_name,
            "attributeDataType": value.attribute_data_type,
            "rawValue": value.raw_value,
            "rawUnit": value.raw_unit,
            "sourceId": value.source_id,
            "evidenceId": value.evidence_id,
            "evidenceType": value.evidence_type,
            "location": value.location,
            "excerpt": value.excerpt,
            "matchedLabel": value.matched_label,
            "matchType": value.match_type,
            "confidenceBp": value.confidence_bp,
            "sourceQualityBp": value.source_quality_bp,
            "parseStatus": value.parse_status,
            "createdAt": value.created_at,
        }

    @staticmethod
    def _from_items(items: list[dict[str, Any]]) -> StructuredAttributeExtractionResult:
        try:
            metadata = next(item for item in items if item["recordKey"] == "META")
            candidate_items = sorted(
                (item for item in items if str(item["recordKey"]).startswith("CANDIDATE#")),
                key=lambda item: str(item["recordKey"]),
            )
            candidates = tuple(
                AttributeCandidate(
                    candidate_id=str(item["candidateId"]),
                    attribute_name=str(item["attributeName"]),
                    attribute_display_name=str(item["attributeDisplayName"]),
                    attribute_data_type=AttributeDataType(str(item["attributeDataType"])),
                    raw_value=None if item.get("rawValue") is None else str(item["rawValue"]),
                    raw_unit=None if item.get("rawUnit") is None else str(item["rawUnit"]),
                    source_id=UUID(str(item["sourceId"])),
                    evidence_id=str(item["evidenceId"]),
                    evidence_type=AttributeExtractionEvidenceType(str(item["evidenceType"])),
                    location=str(item["location"]),
                    excerpt=str(item["excerpt"]),
                    matched_label=str(item["matchedLabel"]),
                    match_type=AttributeMatchType(str(item["matchType"])),
                    confidence_bp=int(item["confidenceBp"]),
                    source_quality_bp=int(item["sourceQualityBp"]),
                    parse_status=AttributeValueParseStatus(str(item["parseStatus"])),
                    created_at=parse_utc(item["createdAt"]),
                )
                for item in candidate_items
            )
            return StructuredAttributeExtractionResult(
                extraction_id=UUID(str(metadata["extractionId"])),
                job_id=UUID(str(metadata["jobId"])),
                product_id=UUID(str(metadata["productId"])),
                classification_id=UUID(str(metadata["classificationId"])),
                category=ProductCategory(str(metadata["category"])),
                schema_version=int(metadata["schemaVersion"]),
                schema_fingerprint=str(metadata["schemaFingerprint"]),
                status=StructuredAttributeExtractionStatus(str(metadata["status"])),
                evidence_item_count=int(metadata["evidenceItemCount"]),
                candidate_count=int(metadata["candidateCount"]),
                distinct_attribute_count=int(metadata["distinctAttributeCount"]),
                duplicate_count=int(metadata["duplicateCount"]),
                candidates=candidates,
                warning_codes=tuple(str(code) for code in metadata.get("warningCodes", [])),
                engine=str(metadata["engine"]),
                engine_version=str(metadata["engineVersion"]),
                created_at=parse_utc(metadata["createdAt"]),
            )
        except (ValueError, KeyError, TypeError, StopIteration) as exc:
            raise StructuredAttributeExtractionSerializationError() from exc
