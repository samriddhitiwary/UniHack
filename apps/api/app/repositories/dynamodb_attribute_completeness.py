"""Composite DynamoDB persistence for attribute completeness results."""

import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    AttributeCompletenessRepositoryError,
    AttributeCompletenessResultAlreadyExistsError,
    AttributeCompletenessResultItemTooLargeError,
    AttributeCompletenessSerializationError,
)
from app.domain.attribute_completeness import (
    AttributeCompletenessAssessment,
    AttributeCompletenessResult,
    AttributeCompletenessState,
    AttributeCompletenessStatus,
)
from app.domain.attribute_conflicts import AttributeConflictType, AttributeConsensusStatus
from app.domain.products import ProductCategory
from app.utils.dynamodb import AttributeValue, WireItem, deserialize_item, parse_utc, serialize_item

JOB_ID_INDEX = "JobIdIndex"
MAX_SAFE_ITEM_BYTES = 390_000


class DynamoDBAttributeCompletenessResultRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client, self._table_name = client, table_name

    def create(self, result: AttributeCompletenessResult) -> AttributeCompletenessResult:
        records = [self._meta(result)] + [
            self._attribute(result.completeness_id, index, item)
            for index, item in enumerate(result.attributes, 1)
        ]
        wire = [serialize_item(record) for record in records]
        if any(
            len(json.dumps(item, separators=(",", ":"), default=str).encode()) > MAX_SAFE_ITEM_BYTES
            for item in wire
        ):
            raise AttributeCompletenessResultItemTooLargeError()
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
                raise AttributeCompletenessResultAlreadyExistsError() from exc
            raise AttributeCompletenessRepositoryError() from exc
        except BotoCoreError as exc:
            raise AttributeCompletenessRepositoryError() from exc
        return result

    def get_by_id(self, completeness_id: UUID) -> AttributeCompletenessResult | None:
        items: list[Mapping[str, AttributeValue]] = []
        start: WireItem | None = None
        try:
            while True:
                request: dict[str, Any] = {
                    "TableName": self._table_name,
                    "KeyConditionExpression": "#id = :id",
                    "ExpressionAttributeNames": {"#id": "completenessId"},
                    "ExpressionAttributeValues": serialize_item({":id": completeness_id}),
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
        except AttributeCompletenessRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, ValueError, TypeError) as exc:
            raise AttributeCompletenessRepositoryError() from exc

    def get_by_job_id(self, job_id: UUID) -> AttributeCompletenessResult | None:
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
            return self.get_by_id(UUID(str(deserialize_item(items[0])["completenessId"])))
        except AttributeCompletenessRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, ValueError, TypeError) as exc:
            raise AttributeCompletenessRepositoryError() from exc

    @staticmethod
    def _meta(result: AttributeCompletenessResult) -> dict[str, Any]:
        record = {
            "completenessId": result.completeness_id,
            "recordKey": "META",
            "jobId": result.job_id,
            "productId": result.product_id,
            "conflictDetectionId": result.conflict_detection_id,
            "normalizationId": result.normalization_id,
            "extractionId": result.extraction_id,
            "classificationId": result.classification_id,
            "category": result.category,
            "schemaVersion": result.schema_version,
            "schemaFingerprint": result.schema_fingerprint,
            "status": result.status,
            "warningCodes": list(result.warning_codes),
            "engine": result.engine,
            "engineVersion": result.engine_version,
            "createdAt": result.created_at,
        }
        for name in _COUNT_AND_BP_FIELDS:
            record[_camel(name)] = getattr(result, name)
        return record

    @staticmethod
    def _attribute(
        result_id: UUID, index: int, item: AttributeCompletenessAssessment
    ) -> dict[str, Any]:
        return {
            "completenessId": result_id,
            "recordKey": f"ATTRIBUTE#{index:06d}",
            "attributeName": item.attribute_name,
            "attributeDisplayName": item.attribute_display_name,
            "required": item.required,
            "displayOrder": item.display_order,
            "state": item.state,
            "candidateCount": item.candidate_count,
            "comparableCandidateCount": item.comparable_candidate_count,
            "distinctSourceCount": item.distinct_source_count,
            "consensusStatus": item.consensus_status,
            "consensusConfidenceBp": item.consensus_confidence_bp,
            "conflictType": item.conflict_type,
            "available": item.available,
            "resolved": item.resolved,
            "verified": item.verified,
            "candidateIds": list(item.candidate_ids),
            "warningCodes": list(item.warning_codes),
        }

    @staticmethod
    def _from_items(items: list[dict[str, Any]]) -> AttributeCompletenessResult:
        try:
            meta = next(item for item in items if item["recordKey"] == "META")
            attribute_items = sorted(
                (item for item in items if str(item["recordKey"]).startswith("ATTRIBUTE#")),
                key=lambda item: str(item["recordKey"]),
            )
            attributes = tuple(
                AttributeCompletenessAssessment(
                    attribute_name=str(item["attributeName"]),
                    attribute_display_name=str(item["attributeDisplayName"]),
                    required=bool(item["required"]),
                    display_order=int(item["displayOrder"]),
                    state=AttributeCompletenessState(str(item["state"])),
                    candidate_count=int(item["candidateCount"]),
                    comparable_candidate_count=int(item["comparableCandidateCount"]),
                    distinct_source_count=int(item["distinctSourceCount"]),
                    consensus_status=None
                    if item.get("consensusStatus") is None
                    else AttributeConsensusStatus(str(item["consensusStatus"])),
                    consensus_confidence_bp=None
                    if item.get("consensusConfidenceBp") is None
                    else int(item["consensusConfidenceBp"]),
                    conflict_type=None
                    if item.get("conflictType") is None
                    else AttributeConflictType(str(item["conflictType"])),
                    available=bool(item["available"]),
                    resolved=bool(item["resolved"]),
                    verified=bool(item["verified"]),
                    candidate_ids=tuple(str(value) for value in item["candidateIds"]),
                    warning_codes=tuple(str(value) for value in item.get("warningCodes", [])),
                )
                for item in attribute_items
            )
            values = {name: int(meta[_camel(name)]) for name in _COUNT_AND_BP_FIELDS}
            return AttributeCompletenessResult(
                completeness_id=UUID(str(meta["completenessId"])),
                job_id=UUID(str(meta["jobId"])),
                product_id=UUID(str(meta["productId"])),
                conflict_detection_id=UUID(str(meta["conflictDetectionId"])),
                normalization_id=UUID(str(meta["normalizationId"])),
                extraction_id=UUID(str(meta["extractionId"])),
                classification_id=UUID(str(meta["classificationId"])),
                category=ProductCategory(str(meta["category"])),
                schema_version=int(meta["schemaVersion"]),
                schema_fingerprint=str(meta["schemaFingerprint"]),
                status=AttributeCompletenessStatus(str(meta["status"])),
                **values,
                attributes=attributes,
                warning_codes=tuple(str(value) for value in meta.get("warningCodes", [])),
                engine=str(meta["engine"]),
                engine_version=str(meta["engineVersion"]),
                created_at=parse_utc(meta["createdAt"]),
            )
        except (ValueError, KeyError, TypeError, StopIteration) as exc:
            raise AttributeCompletenessSerializationError() from exc


_COUNT_AND_BP_FIELDS = (
    "required_attribute_count",
    "required_available_count",
    "required_resolved_count",
    "required_verified_count",
    "required_missing_count",
    "required_conflicted_count",
    "required_indeterminate_count",
    "required_invalid_count",
    "optional_attribute_count",
    "optional_available_count",
    "optional_resolved_count",
    "optional_verified_count",
    "optional_missing_count",
    "optional_conflicted_count",
    "optional_indeterminate_count",
    "optional_invalid_count",
    "total_attribute_count",
    "total_available_count",
    "total_resolved_count",
    "total_verified_count",
    "total_missing_count",
    "total_conflicted_count",
    "total_indeterminate_count",
    "total_invalid_count",
    "required_available_bp",
    "required_resolved_bp",
    "required_verified_bp",
    "overall_available_bp",
    "overall_resolved_bp",
)


def _camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.title() for part in rest)
