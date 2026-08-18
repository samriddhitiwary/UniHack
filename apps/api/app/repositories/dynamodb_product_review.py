"""Transactional composite DynamoDB persistence for product reviews."""

import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    ProductReviewAlreadyCompletedError,
    ProductReviewAlreadyExistsError,
    ProductReviewItemTooLargeError,
    ProductReviewNotFoundError,
    ProductReviewRepositoryError,
    ProductReviewSerializationError,
    ProductReviewVersionConflictError,
)
from app.domain.product_review import (
    AttributeReviewDecision,
    AttributeReviewDecisionType,
    CurrentAttributeReviewDecision,
    ProductReviewSession,
    ProductReviewSessionStatus,
    ReviewDecisionPage,
)
from app.domain.products import ProductCategory
from app.utils.cursors import decode_review_decision_cursor, encode_review_decision_cursor
from app.utils.dynamodb import AttributeValue, WireItem, deserialize_item, parse_utc, serialize_item

MAX_SAFE_ITEM_BYTES = 390_000


class DynamoDBProductReviewRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client, self._table_name = client, table_name

    def create(self, review: ProductReviewSession) -> ProductReviewSession:
        meta = self._meta(review)
        guard = {
            "reviewId": f"SELECTION#{review.selection_id}",
            "recordKey": "REVIEW",
            "selectionId": review.selection_id,
            "targetReviewId": review.review_id,
            "createdAt": review.created_at,
        }
        self._guard_size(meta, guard)
        try:
            self._client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self._table_name,
                            "Item": serialize_item(meta),
                            "ConditionExpression": "attribute_not_exists(#pk)",
                            "ExpressionAttributeNames": {"#pk": "reviewId"},
                        }
                    },
                    {
                        "Put": {
                            "TableName": self._table_name,
                            "Item": serialize_item(guard),
                            "ConditionExpression": "attribute_not_exists(#pk)",
                            "ExpressionAttributeNames": {"#pk": "reviewId"},
                        }
                    },
                ]
            )
        except ClientError as exc:
            if self._error_code(exc) in {
                "TransactionCanceledException",
                "ConditionalCheckFailedException",
            }:
                raise ProductReviewAlreadyExistsError() from exc
            raise ProductReviewRepositoryError("review could not be created") from exc
        except BotoCoreError as exc:
            raise ProductReviewRepositoryError("review could not be created") from exc
        return review

    def get_by_id(self, review_id: UUID) -> ProductReviewSession | None:
        items = self._query_partition(review_id)
        if not items:
            return None
        try:
            meta = next(item for item in items if item.get("recordKey") == "META")
            decisions = {
                str(item["decisionId"]): item
                for item in items
                if str(item.get("recordKey", "")).startswith("DECISION#")
            }
            for current in (
                item for item in items if str(item.get("recordKey", "")).startswith("CURRENT#")
            ):
                decision = decisions.get(str(current.get("decisionId")))
                if decision is None or int(decision["decisionSequence"]) != int(
                    current["decisionSequence"]
                ):
                    raise ProductReviewSerializationError()
            return self._session(meta)
        except ProductReviewSerializationError:
            raise
        except (KeyError, ValueError, TypeError, StopIteration) as exc:
            raise ProductReviewSerializationError() from exc

    def get_by_selection_id(self, selection_id: UUID) -> ProductReviewSession | None:
        try:
            response = self._client.get_item(
                TableName=self._table_name,
                Key=serialize_item(
                    {"reviewId": f"SELECTION#{selection_id}", "recordKey": "REVIEW"}
                ),
                ConsistentRead=True,
            )
            raw = response.get("Item")
            if raw is None:
                return None
            item = deserialize_item(cast(Mapping[str, AttributeValue], raw))
            if str(item.get("selectionId")) != str(selection_id):
                raise ProductReviewSerializationError()
            return self.get_by_id(UUID(str(item["targetReviewId"])))
        except (ProductReviewSerializationError, ProductReviewRepositoryError):
            raise
        except (BotoCoreError, ClientError) as exc:
            raise ProductReviewRepositoryError("review uniqueness could not be read") from exc
        except (KeyError, ValueError, TypeError) as exc:
            raise ProductReviewSerializationError() from exc

    def append_decision(
        self,
        review: ProductReviewSession,
        decision: AttributeReviewDecision,
        current: CurrentAttributeReviewDecision,
        *,
        expected_version: int,
    ) -> ProductReviewSession:
        decision_item, current_item = (
            self._decision(decision),
            self._current(review.review_id, current),
        )
        self._guard_size(decision_item, current_item, self._meta(review))
        try:
            self._client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self._table_name,
                            "Item": serialize_item(decision_item),
                            "ConditionExpression": "attribute_not_exists(#sk)",
                            "ExpressionAttributeNames": {"#sk": "recordKey"},
                        }
                    },
                    {"Put": {"TableName": self._table_name, "Item": serialize_item(current_item)}},
                    {
                        "Update": {
                            "TableName": self._table_name,
                            "Key": serialize_item(
                                {"reviewId": review.review_id, "recordKey": "META"}
                            ),
                            "UpdateExpression": (
                                "SET #version=:version, #decisionCount=:decisionCount, "
                                "#requiredResolved=:requiredResolved, "
                                "#requiredUnresolved=:requiredUnresolved, "
                                "#optionalResolved=:optionalResolved, #updatedAt=:updatedAt"
                            ),
                            "ConditionExpression": "#version=:expected AND #status=:open",
                            "ExpressionAttributeNames": {
                                "#version": "version",
                                "#status": "status",
                                "#decisionCount": "decisionCount",
                                "#requiredResolved": "requiredResolvedCount",
                                "#requiredUnresolved": "requiredUnresolvedCount",
                                "#optionalResolved": "optionalResolvedCount",
                                "#updatedAt": "updatedAt",
                            },
                            "ExpressionAttributeValues": serialize_item(
                                {
                                    ":version": review.version,
                                    ":expected": expected_version,
                                    ":open": ProductReviewSessionStatus.OPEN,
                                    ":decisionCount": review.decision_count,
                                    ":requiredResolved": review.required_resolved_count,
                                    ":requiredUnresolved": review.required_unresolved_count,
                                    ":optionalResolved": review.optional_resolved_count,
                                    ":updatedAt": review.updated_at,
                                }
                            ),
                        }
                    },
                ]
            )
        except ClientError as exc:
            if self._error_code(exc) in {
                "TransactionCanceledException",
                "ConditionalCheckFailedException",
            }:
                self._raise_conflict(review.review_id, expected_version, exc)
            raise ProductReviewRepositoryError("review decision could not be stored") from exc
        except BotoCoreError as exc:
            raise ProductReviewRepositoryError("review decision could not be stored") from exc
        return review

    def list_decisions(
        self, review_id: UUID, *, limit: int, cursor: str | None = None
    ) -> ReviewDecisionPage:
        if isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        start = decode_review_decision_cursor(cursor, review_id)
        request: dict[str, Any] = {
            "TableName": self._table_name,
            "KeyConditionExpression": "#pk=:pk AND begins_with(#sk, :prefix)",
            "ExpressionAttributeNames": {"#pk": "reviewId", "#sk": "recordKey"},
            "ExpressionAttributeValues": serialize_item({":pk": review_id, ":prefix": "DECISION#"}),
            "ScanIndexForward": True,
            "Limit": limit,
            "ConsistentRead": True,
        }
        if start is not None:
            request["ExclusiveStartKey"] = start
        try:
            response = self._client.query(**request)
            items = tuple(
                self._decision_from_item(deserialize_item(item))
                for item in cast(list[Mapping[str, AttributeValue]], response.get("Items", []))
            )
            last = cast(WireItem | None, response.get("LastEvaluatedKey"))
            return ReviewDecisionPage(items, encode_review_decision_cursor(review_id, last))
        except (ProductReviewSerializationError, ValueError):
            raise
        except (BotoCoreError, ClientError, KeyError, TypeError) as exc:
            raise ProductReviewRepositoryError("review decisions could not be listed") from exc

    def list_current_decisions(self, review_id: UUID) -> tuple[CurrentAttributeReviewDecision, ...]:
        try:
            response = self._client.query(
                TableName=self._table_name,
                KeyConditionExpression="#pk=:pk AND begins_with(#sk, :prefix)",
                ExpressionAttributeNames={"#pk": "reviewId", "#sk": "recordKey"},
                ExpressionAttributeValues=serialize_item({":pk": review_id, ":prefix": "CURRENT#"}),
                ConsistentRead=True,
            )
            return tuple(
                self._current_from_item(deserialize_item(item))
                for item in cast(list[Mapping[str, AttributeValue]], response.get("Items", []))
            )
        except ProductReviewSerializationError:
            raise
        except (BotoCoreError, ClientError, KeyError, ValueError, TypeError) as exc:
            raise ProductReviewRepositoryError(
                "current review decisions could not be read"
            ) from exc

    def complete(
        self, review: ProductReviewSession, *, expected_version: int
    ) -> ProductReviewSession:
        try:
            self._client.update_item(
                TableName=self._table_name,
                Key=serialize_item({"reviewId": review.review_id, "recordKey": "META"}),
                UpdateExpression=(
                    "SET #status=:completed, #version=:version, #updatedAt=:updatedAt, "
                    "#completedAt=:completedAt"
                ),
                ConditionExpression="#version=:expected AND #status=:open",
                ExpressionAttributeNames={
                    "#status": "status",
                    "#version": "version",
                    "#updatedAt": "updatedAt",
                    "#completedAt": "completedAt",
                },
                ExpressionAttributeValues=serialize_item(
                    {
                        ":completed": ProductReviewSessionStatus.COMPLETED,
                        ":open": ProductReviewSessionStatus.OPEN,
                        ":version": review.version,
                        ":expected": expected_version,
                        ":updatedAt": review.updated_at,
                        ":completedAt": review.completed_at,
                    }
                ),
            )
        except ClientError as exc:
            if self._error_code(exc) == "ConditionalCheckFailedException":
                self._raise_conflict(review.review_id, expected_version, exc)
            raise ProductReviewRepositoryError("review could not be completed") from exc
        except BotoCoreError as exc:
            raise ProductReviewRepositoryError("review could not be completed") from exc
        return review

    def _query_partition(self, review_id: UUID) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        start: WireItem | None = None
        try:
            while True:
                request: dict[str, Any] = {
                    "TableName": self._table_name,
                    "KeyConditionExpression": "#pk=:pk",
                    "ExpressionAttributeNames": {"#pk": "reviewId"},
                    "ExpressionAttributeValues": serialize_item({":pk": review_id}),
                    "ConsistentRead": True,
                }
                if start:
                    request["ExclusiveStartKey"] = start
                response = self._client.query(**request)
                output.extend(
                    deserialize_item(item)
                    for item in cast(list[Mapping[str, AttributeValue]], response.get("Items", []))
                )
                start = cast(WireItem | None, response.get("LastEvaluatedKey"))
                if not start:
                    return output
        except (BotoCoreError, ClientError) as exc:
            raise ProductReviewRepositoryError("review could not be read") from exc

    def _raise_conflict(self, review_id: UUID, expected_version: int, exc: ClientError) -> None:
        current = self.get_by_id(review_id)
        if current is None:
            raise ProductReviewNotFoundError() from exc
        if current.status is ProductReviewSessionStatus.COMPLETED:
            raise ProductReviewAlreadyCompletedError() from exc
        if current.version != expected_version:
            raise ProductReviewVersionConflictError() from exc
        raise ProductReviewRepositoryError("review conditional write failed") from exc

    @staticmethod
    def _meta(review: ProductReviewSession) -> dict[str, Any]:
        return {
            "reviewId": review.review_id,
            "recordKey": "META",
            "productId": review.product_id,
            "selectionId": review.selection_id,
            "conflictDetectionId": review.conflict_detection_id,
            "validationId": review.validation_id,
            "completenessId": review.completeness_id,
            "normalizationId": review.normalization_id,
            "extractionId": review.extraction_id,
            "classificationId": review.classification_id,
            "category": review.category,
            "schemaVersion": review.schema_version,
            "schemaFingerprint": review.schema_fingerprint,
            "status": review.status,
            "version": review.version,
            "requiredAttributeCount": review.required_attribute_count,
            "requiredResolvedCount": review.required_resolved_count,
            "requiredUnresolvedCount": review.required_unresolved_count,
            "optionalAttributeCount": review.optional_attribute_count,
            "optionalResolvedCount": review.optional_resolved_count,
            "decisionCount": review.decision_count,
            "createdAt": review.created_at,
            "updatedAt": review.updated_at,
            "completedAt": review.completed_at,
        }

    @staticmethod
    def _decision(value: AttributeReviewDecision) -> dict[str, Any]:
        return {
            "reviewId": value.review_id,
            "recordKey": f"DECISION#{value.decision_sequence:06d}",
            "decisionId": value.decision_id,
            "productId": value.product_id,
            "decisionSequence": value.decision_sequence,
            "attributeName": value.attribute_name,
            "decisionType": value.decision_type,
            "candidateId": value.candidate_id,
            "approvedValue": value.approved_value,
            "approvedUnit": value.approved_unit,
            "manualRawValue": value.manual_raw_value,
            "manualRawUnit": value.manual_raw_unit,
            "reviewerId": value.reviewer_id,
            "comment": value.comment,
            "reviewVersion": value.review_version,
            "createdAt": value.created_at,
        }

    @staticmethod
    def _current(review_id: UUID, value: CurrentAttributeReviewDecision) -> dict[str, Any]:
        return {
            "reviewId": review_id,
            "recordKey": f"CURRENT#{value.attribute_name}",
            "attributeName": value.attribute_name,
            "decisionId": value.decision_id,
            "decisionSequence": value.decision_sequence,
            "decisionType": value.decision_type,
            "candidateId": value.candidate_id,
            "approvedValue": value.approved_value,
            "approvedUnit": value.approved_unit,
            "reviewerId": value.reviewer_id,
            "updatedAt": value.updated_at,
        }

    @staticmethod
    def _session(item: dict[str, Any]) -> ProductReviewSession:
        return ProductReviewSession(
            review_id=UUID(str(item["reviewId"])),
            product_id=UUID(str(item["productId"])),
            selection_id=UUID(str(item["selectionId"])),
            conflict_detection_id=UUID(str(item["conflictDetectionId"])),
            validation_id=UUID(str(item["validationId"])),
            completeness_id=UUID(str(item["completenessId"])),
            normalization_id=UUID(str(item["normalizationId"])),
            extraction_id=UUID(str(item["extractionId"])),
            classification_id=UUID(str(item["classificationId"])),
            category=ProductCategory(str(item["category"])),
            schema_version=int(item["schemaVersion"]),
            schema_fingerprint=str(item["schemaFingerprint"]),
            status=ProductReviewSessionStatus(str(item["status"])),
            version=int(item["version"]),
            required_attribute_count=int(item["requiredAttributeCount"]),
            required_resolved_count=int(item["requiredResolvedCount"]),
            required_unresolved_count=int(item["requiredUnresolvedCount"]),
            optional_attribute_count=int(item["optionalAttributeCount"]),
            optional_resolved_count=int(item["optionalResolvedCount"]),
            decision_count=int(item["decisionCount"]),
            created_at=parse_utc(item["createdAt"]),
            updated_at=parse_utc(item["updatedAt"]),
            completed_at=None
            if item.get("completedAt") is None
            else parse_utc(item["completedAt"]),
        )

    @staticmethod
    def _decision_from_item(item: dict[str, Any]) -> AttributeReviewDecision:
        try:
            return AttributeReviewDecision(
                decision_id=UUID(str(item["decisionId"])),
                review_id=UUID(str(item["reviewId"])),
                product_id=UUID(str(item["productId"])),
                decision_sequence=int(item["decisionSequence"]),
                attribute_name=str(item["attributeName"]),
                decision_type=AttributeReviewDecisionType(str(item["decisionType"])),
                candidate_id=None if item.get("candidateId") is None else str(item["candidateId"]),
                approved_value=None
                if item.get("approvedValue") is None
                else str(item["approvedValue"]),
                approved_unit=None
                if item.get("approvedUnit") is None
                else str(item["approvedUnit"]),
                manual_raw_value=None
                if item.get("manualRawValue") is None
                else str(item["manualRawValue"]),
                manual_raw_unit=None
                if item.get("manualRawUnit") is None
                else str(item["manualRawUnit"]),
                comment=None if item.get("comment") is None else str(item["comment"]),
                reviewer_id=str(item["reviewerId"]),
                review_version=int(item["reviewVersion"]),
                created_at=parse_utc(item["createdAt"]),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise ProductReviewSerializationError() from exc

    @staticmethod
    def _current_from_item(item: dict[str, Any]) -> CurrentAttributeReviewDecision:
        try:
            return CurrentAttributeReviewDecision(
                attribute_name=str(item["attributeName"]),
                decision_id=UUID(str(item["decisionId"])),
                decision_sequence=int(item["decisionSequence"]),
                decision_type=AttributeReviewDecisionType(str(item["decisionType"])),
                candidate_id=None if item.get("candidateId") is None else str(item["candidateId"]),
                approved_value=None
                if item.get("approvedValue") is None
                else str(item["approvedValue"]),
                approved_unit=None
                if item.get("approvedUnit") is None
                else str(item["approvedUnit"]),
                reviewer_id=str(item["reviewerId"]),
                updated_at=parse_utc(item["updatedAt"]),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise ProductReviewSerializationError() from exc

    @staticmethod
    def _guard_size(*items: dict[str, Any]) -> None:
        if any(
            len(json.dumps(serialize_item(item), separators=(",", ":"), default=str).encode())
            > MAX_SAFE_ITEM_BYTES
            for item in items
        ):
            raise ProductReviewItemTooLargeError()

    @staticmethod
    def _error_code(exc: ClientError) -> str:
        return str(exc.response.get("Error", {}).get("Code", ""))
