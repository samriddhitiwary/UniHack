"""Composite DynamoDB persistence for conflict detection results."""

import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    AttributeConflictRepositoryError,
    AttributeConflictResultAlreadyExistsError,
    AttributeConflictResultItemTooLargeError,
    AttributeConflictSerializationError,
)
from app.domain.attribute_conflicts import (
    AttributeConflictDetectionResult,
    AttributeConflictType,
    AttributeConsensus,
    AttributeConsensusStatus,
    CandidateAgreementGroup,
    ConflictDetectionResultStatus,
)
from app.domain.category_schemas import AttributeDataType
from app.domain.products import ProductCategory
from app.utils.dynamodb import AttributeValue, WireItem, deserialize_item, parse_utc, serialize_item

JOB_ID_INDEX = "JobIdIndex"
MAX_SAFE_ITEM_BYTES = 390_000


class DynamoDBAttributeConflictDetectionResultRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client, self._table_name = client, table_name

    def create(self, result: AttributeConflictDetectionResult) -> AttributeConflictDetectionResult:
        records = [self._meta(result)]
        for attribute_index, attribute in enumerate(result.attributes, 1):
            records.append(
                self._attribute(result.conflict_detection_id, attribute_index, attribute)
            )
            records.extend(
                self._group(
                    result.conflict_detection_id,
                    attribute_index,
                    group_index,
                    attribute.attribute_name,
                    group,
                )
                for group_index, group in enumerate(attribute.groups, 1)
            )
        wire = [serialize_item(record) for record in records]
        if any(
            len(json.dumps(item, separators=(",", ":"), default=str).encode()) > MAX_SAFE_ITEM_BYTES
            for item in wire
        ):
            raise AttributeConflictResultItemTooLargeError()
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
                raise AttributeConflictResultAlreadyExistsError() from exc
            raise AttributeConflictRepositoryError() from exc
        except BotoCoreError as exc:
            raise AttributeConflictRepositoryError() from exc
        return result

    def get_by_id(self, conflict_detection_id: UUID) -> AttributeConflictDetectionResult | None:
        items: list[Mapping[str, AttributeValue]] = []
        start: WireItem | None = None
        try:
            while True:
                request: dict[str, Any] = {
                    "TableName": self._table_name,
                    "KeyConditionExpression": "#id = :id",
                    "ExpressionAttributeNames": {"#id": "conflictDetectionId"},
                    "ExpressionAttributeValues": serialize_item({":id": conflict_detection_id}),
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
        except AttributeConflictRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, ValueError, TypeError) as exc:
            raise AttributeConflictRepositoryError() from exc

    def get_by_job_id(self, job_id: UUID) -> AttributeConflictDetectionResult | None:
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
            return self.get_by_id(UUID(str(deserialize_item(items[0])["conflictDetectionId"])))
        except AttributeConflictRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, ValueError, TypeError) as exc:
            raise AttributeConflictRepositoryError() from exc

    @staticmethod
    def _meta(result: AttributeConflictDetectionResult) -> dict[str, Any]:
        return {
            "conflictDetectionId": result.conflict_detection_id,
            "recordKey": "META",
            "jobId": result.job_id,
            "productId": result.product_id,
            "normalizationId": result.normalization_id,
            "extractionId": result.extraction_id,
            "classificationId": result.classification_id,
            "category": result.category,
            "schemaVersion": result.schema_version,
            "schemaFingerprint": result.schema_fingerprint,
            "status": result.status,
            "attributeCount": result.attribute_count,
            "agreementCount": result.agreement_count,
            "toleranceAgreementCount": result.tolerance_agreement_count,
            "singleCandidateCount": result.single_candidate_count,
            "conflictCount": result.conflict_count,
            "indeterminateCount": result.indeterminate_count,
            "noValidCandidateCount": result.no_valid_candidate_count,
            "warningCodes": list(result.warning_codes),
            "engine": result.engine,
            "engineVersion": result.engine_version,
            "createdAt": result.created_at,
        }

    @staticmethod
    def _attribute(result_id: UUID, index: int, value: AttributeConsensus) -> dict[str, Any]:
        return {
            "conflictDetectionId": result_id,
            "recordKey": f"ATTRIBUTE#{index:06d}",
            "attributeName": value.attribute_name,
            "attributeDisplayName": value.attribute_display_name,
            "dataType": value.data_type,
            "status": value.status,
            "candidateCount": value.candidate_count,
            "comparableCandidateCount": value.comparable_candidate_count,
            "excludedCandidateCount": value.excluded_candidate_count,
            "distinctSourceCount": value.distinct_source_count,
            "agreementGroupCount": value.agreement_group_count,
            "conflictType": value.conflict_type,
            "candidateIds": list(value.candidate_ids),
            "consensusConfidenceBp": value.consensus_confidence_bp,
            "warningCodes": list(value.warning_codes),
        }

    @staticmethod
    def _group(
        result_id: UUID,
        attribute_index: int,
        group_index: int,
        attribute_name: str,
        value: CandidateAgreementGroup,
    ) -> dict[str, Any]:
        return {
            "conflictDetectionId": result_id,
            "recordKey": f"GROUP#{attribute_index:06d}#{group_index:06d}",
            "attributeIndex": attribute_index,
            "groupId": value.group_id,
            "attributeName": attribute_name,
            "normalizedValue": value.normalized_value,
            "normalizedUnit": value.normalized_unit,
            "candidateIds": list(value.candidate_ids),
            "distinctSourceIds": list(value.distinct_source_ids),
            "candidateCount": value.candidate_count,
            "distinctSourceCount": value.distinct_source_count,
        }

    @staticmethod
    def _from_items(items: list[dict[str, Any]]) -> AttributeConflictDetectionResult:
        try:
            meta = next(item for item in items if item["recordKey"] == "META")
            attribute_items = sorted(
                (item for item in items if str(item["recordKey"]).startswith("ATTRIBUTE#")),
                key=lambda item: str(item["recordKey"]),
            )
            attributes = []
            for index, item in enumerate(attribute_items, 1):
                group_items = sorted(
                    (
                        group
                        for group in items
                        if str(group["recordKey"]).startswith(f"GROUP#{index:06d}#")
                    ),
                    key=lambda group: str(group["recordKey"]),
                )
                groups = tuple(
                    CandidateAgreementGroup(
                        group_id=str(group["groupId"]),
                        normalized_value=str(group["normalizedValue"]),
                        normalized_unit=None
                        if group.get("normalizedUnit") is None
                        else str(group["normalizedUnit"]),
                        candidate_ids=tuple(str(value) for value in group["candidateIds"]),
                        distinct_source_ids=tuple(
                            UUID(str(value)) for value in group["distinctSourceIds"]
                        ),
                        candidate_count=int(group["candidateCount"]),
                        distinct_source_count=int(group["distinctSourceCount"]),
                    )
                    for group in group_items
                )
                attributes.append(
                    AttributeConsensus(
                        attribute_name=str(item["attributeName"]),
                        attribute_display_name=str(item["attributeDisplayName"]),
                        data_type=AttributeDataType(str(item["dataType"])),
                        status=AttributeConsensusStatus(str(item["status"])),
                        candidate_count=int(item["candidateCount"]),
                        comparable_candidate_count=int(item["comparableCandidateCount"]),
                        excluded_candidate_count=int(item["excludedCandidateCount"]),
                        distinct_source_count=int(item["distinctSourceCount"]),
                        agreement_group_count=int(item["agreementGroupCount"]),
                        conflict_type=None
                        if item.get("conflictType") is None
                        else AttributeConflictType(str(item["conflictType"])),
                        candidate_ids=tuple(str(value) for value in item["candidateIds"]),
                        groups=groups,
                        consensus_confidence_bp=int(item["consensusConfidenceBp"]),
                        warning_codes=tuple(str(value) for value in item.get("warningCodes", [])),
                    )
                )
            return AttributeConflictDetectionResult(
                conflict_detection_id=UUID(str(meta["conflictDetectionId"])),
                job_id=UUID(str(meta["jobId"])),
                product_id=UUID(str(meta["productId"])),
                normalization_id=UUID(str(meta["normalizationId"])),
                extraction_id=UUID(str(meta["extractionId"])),
                classification_id=UUID(str(meta["classificationId"])),
                category=ProductCategory(str(meta["category"])),
                schema_version=int(meta["schemaVersion"]),
                schema_fingerprint=str(meta["schemaFingerprint"]),
                status=ConflictDetectionResultStatus(str(meta["status"])),
                attribute_count=int(meta["attributeCount"]),
                agreement_count=int(meta["agreementCount"]),
                tolerance_agreement_count=int(meta["toleranceAgreementCount"]),
                single_candidate_count=int(meta["singleCandidateCount"]),
                conflict_count=int(meta["conflictCount"]),
                indeterminate_count=int(meta["indeterminateCount"]),
                no_valid_candidate_count=int(meta["noValidCandidateCount"]),
                attributes=tuple(attributes),
                warning_codes=tuple(str(value) for value in meta.get("warningCodes", [])),
                engine=str(meta["engine"]),
                engine_version=str(meta["engineVersion"]),
                created_at=parse_utc(meta["createdAt"]),
            )
        except (ValueError, KeyError, TypeError, StopIteration) as exc:
            raise AttributeConflictSerializationError() from exc
