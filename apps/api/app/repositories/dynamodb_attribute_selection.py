"""Composite DynamoDB persistence for attribute selection results."""

import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    AttributeSelectionRepositoryError,
    AttributeSelectionResultAlreadyExistsError,
    AttributeSelectionResultItemTooLargeError,
    AttributeSelectionSerializationError,
)
from app.domain.attribute_conflicts import AttributeConflictType, AttributeConsensusStatus
from app.domain.attribute_selection import (
    AttributeSelectionResult,
    AttributeSelectionStatus,
    ProductReviewPreparationSummary,
    ProductReviewStatus,
    ProposedAttributeSelection,
    SelectionReasonCode,
)
from app.domain.products import ProductCategory
from app.utils.dynamodb import AttributeValue, WireItem, deserialize_item, parse_utc, serialize_item

JOB_ID_INDEX = "JobIdIndex"
MAX_SAFE_ITEM_BYTES = 390_000


class DynamoDBAttributeSelectionResultRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client, self._table_name = client, table_name

    def create(self, result: AttributeSelectionResult) -> AttributeSelectionResult:
        records = [self._meta(result)] + [
            self._attribute(result.selection_id, index, item)
            for index, item in enumerate(result.attributes, 1)
        ]
        wire = [serialize_item(record) for record in records]
        if any(
            len(json.dumps(item, separators=(",", ":"), default=str).encode()) > MAX_SAFE_ITEM_BYTES
            for item in wire
        ):
            raise AttributeSelectionResultItemTooLargeError()
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
                raise AttributeSelectionResultAlreadyExistsError() from exc
            raise AttributeSelectionRepositoryError() from exc
        except BotoCoreError as exc:
            raise AttributeSelectionRepositoryError() from exc
        return result

    def get_by_id(self, selection_id: UUID) -> AttributeSelectionResult | None:
        items: list[Mapping[str, AttributeValue]] = []
        start: WireItem | None = None
        try:
            while True:
                request: dict[str, Any] = {
                    "TableName": self._table_name,
                    "KeyConditionExpression": "#id = :id",
                    "ExpressionAttributeNames": {"#id": "selectionId"},
                    "ExpressionAttributeValues": serialize_item({":id": selection_id}),
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
        except AttributeSelectionRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, ValueError, TypeError) as exc:
            raise AttributeSelectionRepositoryError() from exc

    def get_by_job_id(self, job_id: UUID) -> AttributeSelectionResult | None:
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
            return self.get_by_id(UUID(str(deserialize_item(items[0])["selectionId"])))
        except AttributeSelectionRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, ValueError, TypeError) as exc:
            raise AttributeSelectionRepositoryError() from exc

    @staticmethod
    def _meta(result: AttributeSelectionResult) -> dict[str, Any]:
        record = {
            "selectionId": result.selection_id,
            "recordKey": "META",
            "jobId": result.job_id,
            "productId": result.product_id,
            "conflictDetectionId": result.conflict_detection_id,
            "validationId": result.validation_id,
            "completenessId": result.completeness_id,
            "normalizationId": result.normalization_id,
            "extractionId": result.extraction_id,
            "classificationId": result.classification_id,
            "category": result.category,
            "schemaVersion": result.schema_version,
            "schemaFingerprint": result.schema_fingerprint,
            "overallStatus": result.overall_status,
            "warningCodes": list(result.warning_codes),
            "engine": result.engine,
            "engineVersion": result.engine_version,
            "createdAt": result.created_at,
        }
        for name in _COUNT_FIELDS:
            record[_camel(name)] = getattr(result, name)
        summary = result.review_summary
        for name in _SUMMARY_FIELDS:
            record[_summary_key(name)] = getattr(summary, name)
        return record

    @staticmethod
    def _attribute(
        selection_id: UUID, index: int, item: ProposedAttributeSelection
    ) -> dict[str, Any]:
        return {
            "selectionId": selection_id,
            "recordKey": f"ATTRIBUTE#{index:06d}",
            "attributeName": item.attribute_name,
            "attributeDisplayName": item.attribute_display_name,
            "required": item.required,
            "displayOrder": item.display_order,
            "selectionStatus": item.selection_status,
            "reviewRequired": item.review_required,
            "proposedValue": item.proposed_value,
            "proposedUnit": item.proposed_unit,
            "primaryCandidateId": item.primary_candidate_id,
            "supportingCandidateIds": list(item.supporting_candidate_ids),
            "reviewCandidateIds": list(item.review_candidate_ids),
            "candidateCount": item.candidate_count,
            "validCandidateCount": item.valid_candidate_count,
            "distinctSourceCount": item.distinct_source_count,
            "consensusStatus": item.consensus_status,
            "conflictType": item.conflict_type,
            "selectionConfidenceBp": item.selection_confidence_bp,
            "reasonCodes": list(item.reason_codes),
            "warningCodes": list(item.warning_codes),
        }

    @staticmethod
    def _from_items(items: list[dict[str, Any]]) -> AttributeSelectionResult:
        try:
            meta = next(item for item in items if item["recordKey"] == "META")
            records = sorted(
                (item for item in items if str(item["recordKey"]).startswith("ATTRIBUTE#")),
                key=lambda item: str(item["recordKey"]),
            )
            attributes = tuple(
                ProposedAttributeSelection(
                    attribute_name=str(i["attributeName"]),
                    attribute_display_name=str(i["attributeDisplayName"]),
                    required=bool(i["required"]),
                    display_order=int(i["displayOrder"]),
                    selection_status=AttributeSelectionStatus(str(i["selectionStatus"])),
                    review_required=bool(i["reviewRequired"]),
                    proposed_value=None
                    if i.get("proposedValue") is None
                    else str(i["proposedValue"]),
                    proposed_unit=None if i.get("proposedUnit") is None else str(i["proposedUnit"]),
                    primary_candidate_id=None
                    if i.get("primaryCandidateId") is None
                    else str(i["primaryCandidateId"]),
                    supporting_candidate_ids=tuple(str(v) for v in i["supportingCandidateIds"]),
                    review_candidate_ids=tuple(str(v) for v in i["reviewCandidateIds"]),
                    candidate_count=int(i["candidateCount"]),
                    valid_candidate_count=int(i["validCandidateCount"]),
                    distinct_source_count=int(i["distinctSourceCount"]),
                    consensus_status=None
                    if i.get("consensusStatus") is None
                    else AttributeConsensusStatus(str(i["consensusStatus"])),
                    conflict_type=None
                    if i.get("conflictType") is None
                    else AttributeConflictType(str(i["conflictType"])),
                    selection_confidence_bp=int(i["selectionConfidenceBp"]),
                    reason_codes=tuple(SelectionReasonCode(str(v)) for v in i["reasonCodes"]),
                    warning_codes=tuple(str(v) for v in i["warningCodes"]),
                )
                for i in records
            )
            summary = ProductReviewPreparationSummary(
                required_attribute_count=int(meta[_summary_key("required_attribute_count")]),
                auto_selected_required_count=int(
                    meta[_summary_key("auto_selected_required_count")]
                ),
                review_required_required_count=int(
                    meta[_summary_key("review_required_required_count")]
                ),
                missing_required_count=int(meta[_summary_key("missing_required_count")]),
                invalid_required_count=int(meta[_summary_key("invalid_required_count")]),
                optional_attribute_count=int(meta[_summary_key("optional_attribute_count")]),
                auto_selected_optional_count=int(
                    meta[_summary_key("auto_selected_optional_count")]
                ),
                review_required_optional_count=int(
                    meta[_summary_key("review_required_optional_count")]
                ),
                unresolved_optional_count=int(meta[_summary_key("unresolved_optional_count")]),
                auto_selected_total_count=int(meta[_summary_key("auto_selected_total_count")]),
                review_required_total_count=int(meta[_summary_key("review_required_total_count")]),
                overall_status=ProductReviewStatus(str(meta["overallStatus"])),
            )
            return AttributeSelectionResult(
                selection_id=UUID(str(meta["selectionId"])),
                job_id=UUID(str(meta["jobId"])),
                product_id=UUID(str(meta["productId"])),
                conflict_detection_id=UUID(str(meta["conflictDetectionId"])),
                validation_id=UUID(str(meta["validationId"])),
                completeness_id=UUID(str(meta["completenessId"])),
                normalization_id=UUID(str(meta["normalizationId"])),
                extraction_id=UUID(str(meta["extractionId"])),
                classification_id=UUID(str(meta["classificationId"])),
                category=ProductCategory(str(meta["category"])),
                schema_version=int(meta["schemaVersion"]),
                schema_fingerprint=str(meta["schemaFingerprint"]),
                overall_status=ProductReviewStatus(str(meta["overallStatus"])),
                **{name: int(meta[_camel(name)]) for name in _COUNT_FIELDS},
                attributes=attributes,
                review_summary=summary,
                warning_codes=tuple(str(v) for v in meta.get("warningCodes", [])),
                engine=str(meta["engine"]),
                engine_version=str(meta["engineVersion"]),
                created_at=parse_utc(meta["createdAt"]),
            )
        except (ValueError, KeyError, TypeError, StopIteration) as exc:
            raise AttributeSelectionSerializationError() from exc


_COUNT_FIELDS = (
    "attribute_count",
    "auto_selected_count",
    "review_required_count",
    "no_candidate_count",
    "no_valid_candidate_count",
    "required_auto_selected_count",
    "required_review_required_count",
    "required_missing_count",
    "required_invalid_count",
)
_SUMMARY_FIELDS = (
    "required_attribute_count",
    "auto_selected_required_count",
    "review_required_required_count",
    "missing_required_count",
    "invalid_required_count",
    "optional_attribute_count",
    "auto_selected_optional_count",
    "review_required_optional_count",
    "unresolved_optional_count",
    "auto_selected_total_count",
    "review_required_total_count",
    "overall_status",
)


def _camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.title() for part in rest)


def _summary_key(value: str) -> str:
    camel = _camel(value)
    return "summary" + camel[0].upper() + camel[1:]
