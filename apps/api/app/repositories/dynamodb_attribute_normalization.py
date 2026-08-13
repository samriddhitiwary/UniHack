"""Composite DynamoDB persistence for attribute normalization results."""

import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    AttributeNormalizationRepositoryError,
    AttributeNormalizationResultAlreadyExistsError,
    AttributeNormalizationResultItemTooLargeError,
    AttributeNormalizationSerializationError,
)
from app.domain.attribute_extraction import AttributeExtractionEvidenceType
from app.domain.attribute_normalization import (
    AttributeNormalizationResult,
    AttributeNormalizationResultStatus,
    NormalizationStatus,
    NormalizedAttributeCandidate,
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


class DynamoDBAttributeNormalizationResultRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client, self._table_name = client, table_name

    def create(self, result: AttributeNormalizationResult) -> AttributeNormalizationResult:
        records = [self._metadata(result)] + [
            self._candidate(result.normalization_id, index, candidate)
            for index, candidate in enumerate(result.candidates, 1)
        ]
        wire = [serialize_item(record) for record in records]
        if any(
            len(json.dumps(item, separators=(",", ":"), default=str).encode()) > MAX_SAFE_ITEM_BYTES
            for item in wire
        ):
            raise AttributeNormalizationResultItemTooLargeError()
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
                raise AttributeNormalizationResultAlreadyExistsError() from exc
            raise AttributeNormalizationRepositoryError() from exc
        except BotoCoreError as exc:
            raise AttributeNormalizationRepositoryError() from exc
        return result

    def get_by_id(self, normalization_id: UUID) -> AttributeNormalizationResult | None:
        items: list[Mapping[str, AttributeValue]] = []
        start: WireItem | None = None
        try:
            while True:
                request: dict[str, Any] = {
                    "TableName": self._table_name,
                    "KeyConditionExpression": "#normalizationId = :normalizationId",
                    "ExpressionAttributeNames": {"#normalizationId": "normalizationId"},
                    "ExpressionAttributeValues": serialize_item(
                        {":normalizationId": normalization_id}
                    ),
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
        except AttributeNormalizationRepositoryError:
            raise
        except (BotoCoreError, ClientError, ValueError, KeyError, TypeError) as exc:
            raise AttributeNormalizationRepositoryError() from exc

    def get_by_job_id(self, job_id: UUID) -> AttributeNormalizationResult | None:
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
            if not items:
                return None
            metadata = deserialize_item(items[0])
            return self.get_by_id(UUID(str(metadata["normalizationId"])))
        except AttributeNormalizationRepositoryError:
            raise
        except (BotoCoreError, ClientError, ValueError, KeyError, TypeError) as exc:
            raise AttributeNormalizationRepositoryError() from exc

    @staticmethod
    def _metadata(result: AttributeNormalizationResult) -> dict[str, Any]:
        return {
            "normalizationId": result.normalization_id,
            "recordKey": "META",
            "jobId": result.job_id,
            "productId": result.product_id,
            "extractionId": result.extraction_id,
            "classificationId": result.classification_id,
            "category": result.category,
            "schemaVersion": result.schema_version,
            "schemaFingerprint": result.schema_fingerprint,
            "status": result.status,
            "candidateCount": result.candidate_count,
            "normalizedCount": result.normalized_count,
            "convertedCount": result.converted_count,
            "unitMissingCount": result.unit_missing_count,
            "unsupportedUnitCount": result.unsupported_unit_count,
            "invalidValueCount": result.invalid_value_count,
            "warningCodes": list(result.warning_codes),
            "engine": result.engine,
            "engineVersion": result.engine_version,
            "createdAt": result.created_at,
        }

    @staticmethod
    def _candidate(
        normalization_id: UUID, index: int, value: NormalizedAttributeCandidate
    ) -> dict[str, Any]:
        return {
            "normalizationId": normalization_id,
            "recordKey": f"CANDIDATE#{index:06d}",
            "normalizedCandidateId": value.normalized_candidate_id,
            "sourceCandidateId": value.source_candidate_id,
            "sourceExtractionId": value.source_extraction_id,
            "classificationId": value.classification_id,
            "category": value.category,
            "schemaVersion": value.schema_version,
            "schemaFingerprint": value.schema_fingerprint,
            "attributeName": value.attribute_name,
            "attributeDisplayName": value.attribute_display_name,
            "dataType": value.data_type,
            "rawValue": value.raw_value,
            "rawUnit": value.raw_unit,
            "normalizedValue": value.normalized_value,
            "normalizedUnit": value.normalized_unit,
            "normalizationStatus": value.normalization_status,
            "conversionApplied": value.conversion_applied,
            "unitCanonicalizationApplied": value.unit_canonicalization_applied,
            "conversionRule": value.conversion_rule,
            "sourceId": value.source_id,
            "evidenceType": value.evidence_type,
            "evidenceLocation": value.evidence_location,
            "evidenceExcerpt": value.evidence_excerpt,
            "extractionConfidenceBp": value.extraction_confidence_bp,
            "normalizationConfidenceBp": value.normalization_confidence_bp,
            "createdAt": value.created_at,
        }

    @staticmethod
    def _from_items(items: list[dict[str, Any]]) -> AttributeNormalizationResult:
        try:
            metadata = next(item for item in items if item["recordKey"] == "META")
            records = sorted(
                (item for item in items if str(item["recordKey"]).startswith("CANDIDATE#")),
                key=lambda item: str(item["recordKey"]),
            )
            candidates = tuple(
                NormalizedAttributeCandidate(
                    normalized_candidate_id=str(item["normalizedCandidateId"]),
                    source_candidate_id=str(item["sourceCandidateId"]),
                    source_extraction_id=UUID(str(item["sourceExtractionId"])),
                    classification_id=UUID(str(item["classificationId"])),
                    category=ProductCategory(str(item["category"])),
                    schema_version=int(item["schemaVersion"]),
                    schema_fingerprint=str(item["schemaFingerprint"]),
                    attribute_name=str(item["attributeName"]),
                    attribute_display_name=str(item["attributeDisplayName"]),
                    data_type=AttributeDataType(str(item["dataType"])),
                    raw_value=None if item.get("rawValue") is None else str(item["rawValue"]),
                    raw_unit=None if item.get("rawUnit") is None else str(item["rawUnit"]),
                    normalized_value=(
                        None
                        if item.get("normalizedValue") is None
                        else str(item["normalizedValue"])
                    ),
                    normalized_unit=(
                        None if item.get("normalizedUnit") is None else str(item["normalizedUnit"])
                    ),
                    normalization_status=NormalizationStatus(str(item["normalizationStatus"])),
                    conversion_applied=bool(item["conversionApplied"]),
                    unit_canonicalization_applied=bool(item["unitCanonicalizationApplied"]),
                    conversion_rule=(
                        None if item.get("conversionRule") is None else str(item["conversionRule"])
                    ),
                    source_id=UUID(str(item["sourceId"])),
                    evidence_type=AttributeExtractionEvidenceType(str(item["evidenceType"])),
                    evidence_location=str(item["evidenceLocation"]),
                    evidence_excerpt=str(item["evidenceExcerpt"]),
                    extraction_confidence_bp=int(item["extractionConfidenceBp"]),
                    normalization_confidence_bp=int(item["normalizationConfidenceBp"]),
                    created_at=parse_utc(item["createdAt"]),
                )
                for item in records
            )
            return AttributeNormalizationResult(
                normalization_id=UUID(str(metadata["normalizationId"])),
                job_id=UUID(str(metadata["jobId"])),
                product_id=UUID(str(metadata["productId"])),
                extraction_id=UUID(str(metadata["extractionId"])),
                classification_id=UUID(str(metadata["classificationId"])),
                category=ProductCategory(str(metadata["category"])),
                schema_version=int(metadata["schemaVersion"]),
                schema_fingerprint=str(metadata["schemaFingerprint"]),
                status=AttributeNormalizationResultStatus(str(metadata["status"])),
                candidate_count=int(metadata["candidateCount"]),
                normalized_count=int(metadata["normalizedCount"]),
                converted_count=int(metadata["convertedCount"]),
                unit_missing_count=int(metadata["unitMissingCount"]),
                unsupported_unit_count=int(metadata["unsupportedUnitCount"]),
                invalid_value_count=int(metadata["invalidValueCount"]),
                candidates=candidates,
                warning_codes=tuple(str(code) for code in metadata.get("warningCodes", [])),
                engine=str(metadata["engine"]),
                engine_version=str(metadata["engineVersion"]),
                created_at=parse_utc(metadata["createdAt"]),
            )
        except (ValueError, KeyError, TypeError, StopIteration) as exc:
            raise AttributeNormalizationSerializationError() from exc
