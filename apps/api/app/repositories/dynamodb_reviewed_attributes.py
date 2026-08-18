"""Immutable DynamoDB persistence for final reviewed attribute sets."""

import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    ReviewedAttributeRepositoryError,
    ReviewedAttributeSerializationError,
    ReviewedMaterializationAlreadyExistsError,
    ReviewedMaterializationResultItemTooLargeError,
)
from app.domain.attribute_validation import CandidateValidationStatus
from app.domain.category_schemas import AttributeDataType
from app.domain.products import ProductCategory
from app.domain.reviewed_attributes import (
    FinalAttributeOrigin,
    FinalReviewedAttribute,
    FinalReviewedAttributeSet,
    ReviewedAttributeSetStatus,
)
from app.utils.dynamodb import AttributeValue, WireItem, deserialize_item, parse_utc, serialize_item

JOB_ID_INDEX = "JobIdIndex"
REVIEW_ID_INDEX = "ReviewIdIndex"
MAX_SAFE_ITEM_BYTES = 390_000


class DynamoDBFinalReviewedAttributeRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client, self._table_name = client, table_name

    def create(self, result: FinalReviewedAttributeSet) -> FinalReviewedAttributeSet:
        meta = self._meta(result)
        guard = {
            "materializationId": f"REVIEW#{result.review_id}",
            "recordKey": "MATERIALIZATION",
            "targetMaterializationId": result.materialization_id,
        }
        attributes = [
            self._attribute(result.materialization_id, index, value)
            for index, value in enumerate(result.attributes, 1)
        ]
        self._guard_size(meta, guard, *attributes)
        try:
            self._client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self._table_name,
                            "Item": serialize_item(meta),
                            "ConditionExpression": "attribute_not_exists(#pk)",
                            "ExpressionAttributeNames": {"#pk": "materializationId"},
                        }
                    },
                    {
                        "Put": {
                            "TableName": self._table_name,
                            "Item": serialize_item(guard),
                            "ConditionExpression": "attribute_not_exists(#pk)",
                            "ExpressionAttributeNames": {"#pk": "materializationId"},
                        }
                    },
                ]
            )
            for item in attributes:
                self._client.put_item(
                    TableName=self._table_name,
                    Item=serialize_item(item),
                    ConditionExpression="attribute_not_exists(#sk)",
                    ExpressionAttributeNames={"#sk": "recordKey"},
                )
        except ClientError as exc:
            if self._code(exc) in {
                "TransactionCanceledException",
                "ConditionalCheckFailedException",
            }:
                raise ReviewedMaterializationAlreadyExistsError() from exc
            raise ReviewedAttributeRepositoryError() from exc
        except BotoCoreError as exc:
            raise ReviewedAttributeRepositoryError() from exc
        return result

    def get_by_id(self, materialization_id: UUID) -> FinalReviewedAttributeSet | None:
        items: list[dict[str, Any]] = []
        start: WireItem | None = None
        try:
            while True:
                request: dict[str, Any] = {
                    "TableName": self._table_name,
                    "KeyConditionExpression": "#id=:id",
                    "ExpressionAttributeNames": {"#id": "materializationId"},
                    "ExpressionAttributeValues": serialize_item({":id": materialization_id}),
                    "ConsistentRead": True,
                }
                if start:
                    request["ExclusiveStartKey"] = start
                response = self._client.query(**request)
                items.extend(
                    deserialize_item(item)
                    for item in cast(list[Mapping[str, AttributeValue]], response.get("Items", []))
                )
                start = cast(WireItem | None, response.get("LastEvaluatedKey"))
                if not start:
                    break
            return self._from_items(items) if items else None
        except ReviewedAttributeSerializationError:
            raise
        except (BotoCoreError, ClientError, KeyError, ValueError, TypeError) as exc:
            raise ReviewedAttributeRepositoryError() from exc

    def get_by_job_id(self, job_id: UUID) -> FinalReviewedAttributeSet | None:
        return self._get_by_index(JOB_ID_INDEX, "jobId", job_id)

    def get_by_review_id(self, review_id: UUID) -> FinalReviewedAttributeSet | None:
        return self._get_by_index(REVIEW_ID_INDEX, "reviewId", review_id)

    def _get_by_index(self, index: str, key: str, value: UUID) -> FinalReviewedAttributeSet | None:
        try:
            response = self._client.query(
                TableName=self._table_name,
                IndexName=index,
                KeyConditionExpression="#key=:value",
                ExpressionAttributeNames={"#key": key},
                ExpressionAttributeValues=serialize_item({":value": value}),
                ScanIndexForward=False,
                Limit=1,
            )
            items = response.get("Items", [])
            return (
                None
                if not items
                else self.get_by_id(UUID(str(deserialize_item(items[0])["materializationId"])))
            )
        except ReviewedAttributeRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, ValueError, TypeError) as exc:
            raise ReviewedAttributeRepositoryError() from exc

    @staticmethod
    def _meta(result: FinalReviewedAttributeSet) -> dict[str, Any]:
        return {
            "materializationId": result.materialization_id,
            "recordKey": "META",
            "jobId": result.job_id,
            "productId": result.product_id,
            "reviewId": result.review_id,
            "selectionId": result.selection_id,
            "conflictDetectionId": result.conflict_detection_id,
            "validationId": result.validation_id,
            "completenessId": result.completeness_id,
            "normalizationId": result.normalization_id,
            "extractionId": result.extraction_id,
            "classificationId": result.classification_id,
            "category": result.category,
            "schemaVersion": result.schema_version,
            "schemaFingerprint": result.schema_fingerprint,
            "status": result.status,
            "requiredAttributeCount": result.required_attribute_count,
            "materializedRequiredCount": result.materialized_required_count,
            "optionalAttributeCount": result.optional_attribute_count,
            "materializedOptionalCount": result.materialized_optional_count,
            "unresolvedOptionalCount": result.unresolved_optional_count,
            "attributeCount": result.attribute_count,
            "engine": result.engine,
            "engineVersion": result.engine_version,
            "createdAt": result.created_at,
        }

    @staticmethod
    def _attribute(
        materialization_id: UUID, index: int, value: FinalReviewedAttribute
    ) -> dict[str, Any]:
        return {
            "materializationId": materialization_id,
            "recordKey": f"ATTRIBUTE#{index:06d}",
            "attributeName": value.attribute_name,
            "attributeDisplayName": value.attribute_display_name,
            "dataType": value.data_type,
            "required": value.required,
            "displayOrder": value.display_order,
            "value": value.value,
            "unit": value.unit,
            "origin": value.origin,
            "reviewDecisionId": value.review_decision_id,
            "reviewDecisionSequence": value.review_decision_sequence,
            "reviewerId": value.reviewer_id,
            "candidateId": value.candidate_id,
            "sourceCandidateId": value.source_candidate_id,
            "sourceId": value.source_id,
            "manualRawValue": value.manual_raw_value,
            "manualRawUnit": value.manual_raw_unit,
            "selectionConfidenceBp": value.selection_confidence_bp,
            "validationStatus": value.validation_status,
            "createdAt": value.created_at,
        }

    @staticmethod
    def _from_items(items: list[dict[str, Any]]) -> FinalReviewedAttributeSet:
        try:
            meta = next(item for item in items if item["recordKey"] == "META")
            records = sorted(
                (item for item in items if str(item["recordKey"]).startswith("ATTRIBUTE#")),
                key=lambda item: str(item["recordKey"]),
            )
            attributes = tuple(
                FinalReviewedAttribute(
                    attribute_name=str(i["attributeName"]),
                    attribute_display_name=str(i["attributeDisplayName"]),
                    data_type=AttributeDataType(str(i["dataType"])),
                    required=bool(i["required"]),
                    display_order=int(i["displayOrder"]),
                    value=str(i["value"]),
                    unit=None if i.get("unit") is None else str(i["unit"]),
                    origin=FinalAttributeOrigin(str(i["origin"])),
                    review_decision_id=UUID(str(i["reviewDecisionId"])),
                    review_decision_sequence=int(i["reviewDecisionSequence"]),
                    reviewer_id=str(i["reviewerId"]),
                    candidate_id=None if i.get("candidateId") is None else str(i["candidateId"]),
                    source_candidate_id=None
                    if i.get("sourceCandidateId") is None
                    else str(i["sourceCandidateId"]),
                    source_id=None if i.get("sourceId") is None else UUID(str(i["sourceId"])),
                    manual_raw_value=None
                    if i.get("manualRawValue") is None
                    else str(i["manualRawValue"]),
                    manual_raw_unit=None
                    if i.get("manualRawUnit") is None
                    else str(i["manualRawUnit"]),
                    selection_confidence_bp=None
                    if i.get("selectionConfidenceBp") is None
                    else int(i["selectionConfidenceBp"]),
                    validation_status=None
                    if i.get("validationStatus") is None
                    else CandidateValidationStatus(str(i["validationStatus"])),
                    created_at=parse_utc(i["createdAt"]),
                )
                for i in records
            )
            if len(attributes) != int(meta["attributeCount"]):
                raise ReviewedAttributeSerializationError()
            return FinalReviewedAttributeSet(
                materialization_id=UUID(str(meta["materializationId"])),
                job_id=UUID(str(meta["jobId"])),
                product_id=UUID(str(meta["productId"])),
                review_id=UUID(str(meta["reviewId"])),
                selection_id=UUID(str(meta["selectionId"])),
                conflict_detection_id=UUID(str(meta["conflictDetectionId"])),
                validation_id=UUID(str(meta["validationId"])),
                completeness_id=UUID(str(meta["completenessId"])),
                normalization_id=UUID(str(meta["normalizationId"])),
                extraction_id=UUID(str(meta["extractionId"])),
                classification_id=UUID(str(meta["classificationId"])),
                category=ProductCategory(str(meta["category"])),
                schema_version=int(meta["schemaVersion"]),
                schema_fingerprint=str(meta["schemaFingerprint"]),
                status=ReviewedAttributeSetStatus(str(meta["status"])),
                required_attribute_count=int(meta["requiredAttributeCount"]),
                materialized_required_count=int(meta["materializedRequiredCount"]),
                optional_attribute_count=int(meta["optionalAttributeCount"]),
                materialized_optional_count=int(meta["materializedOptionalCount"]),
                unresolved_optional_count=int(meta["unresolvedOptionalCount"]),
                attribute_count=int(meta["attributeCount"]),
                attributes=attributes,
                engine=str(meta["engine"]),
                engine_version=str(meta["engineVersion"]),
                created_at=parse_utc(meta["createdAt"]),
            )
        except ReviewedAttributeSerializationError:
            raise
        except (KeyError, ValueError, TypeError, StopIteration) as exc:
            raise ReviewedAttributeSerializationError() from exc

    @staticmethod
    def _guard_size(*items: dict[str, Any]) -> None:
        if any(
            len(json.dumps(serialize_item(item), separators=(",", ":"), default=str).encode())
            > MAX_SAFE_ITEM_BYTES
            for item in items
        ):
            raise ReviewedMaterializationResultItemTooLargeError()

    @staticmethod
    def _code(exc: ClientError) -> str:
        return str(exc.response.get("Error", {}).get("Code", ""))
