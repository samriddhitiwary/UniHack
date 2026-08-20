"""Versioned DynamoDB persistence for Catalog Intelligence workflows."""

import base64
import binascii
import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    CatalogWorkflowAlreadyActiveError,
    CatalogWorkflowRepositoryError,
    CatalogWorkflowVersionConflictError,
    InvalidCatalogWorkflowCursorError,
)
from app.domain.catalog_workflow import (
    TERMINAL_WORKFLOW_STATUSES,
    CatalogIntelligenceWorkflow,
    CatalogIntelligenceWorkflowConfiguration,
    CatalogIntelligenceWorkflowStage,
    CatalogWorkflowHistoryItem,
    CatalogWorkflowHistoryPage,
    CatalogWorkflowSourceSnapshot,
    CatalogWorkflowStageName,
    CatalogWorkflowStageStatus,
    CatalogWorkflowStatus,
)
from app.domain.product_sources import ProductSourceType
from app.utils.dynamodb import (
    AttributeValue,
    WireItem,
    deserialize_item,
    parse_utc,
    serialize_item,
)

PRODUCT_CREATED_AT_INDEX = "ProductCreatedAtIndex"
MAX_SAFE_ITEM_BYTES = 390_000


class DynamoDBCatalogIntelligenceWorkflowRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client = client
        self._table_name = table_name

    def create(self, workflow: CatalogIntelligenceWorkflow) -> CatalogIntelligenceWorkflow:
        records = [
            self._meta(workflow),
            *(self._stage(workflow.workflow_id, s) for s in workflow.stages),
        ]
        self._guard_size(*records)
        guard = {
            "workflowId": f"ACTIVE_PRODUCT#{workflow.product_id}",
            "recordKey": "GUARD",
            "targetWorkflowId": workflow.workflow_id,
        }
        transaction = [
            {
                "Put": {
                    "TableName": self._table_name,
                    "Item": serialize_item(guard),
                    "ConditionExpression": "attribute_not_exists(#pk)",
                    "ExpressionAttributeNames": {"#pk": "workflowId"},
                }
            },
            *(
                {
                    "Put": {
                        "TableName": self._table_name,
                        "Item": serialize_item(record),
                        "ConditionExpression": "attribute_not_exists(#pk)",
                        "ExpressionAttributeNames": {"#pk": "workflowId"},
                    }
                }
                for record in records
            ),
        ]
        try:
            self._client.transact_write_items(TransactItems=transaction)
        except ClientError as exc:
            if _error_code(exc) in {
                "TransactionCanceledException",
                "ConditionalCheckFailedException",
            }:
                raise CatalogWorkflowAlreadyActiveError() from exc
            raise CatalogWorkflowRepositoryError() from exc
        except BotoCoreError as exc:
            raise CatalogWorkflowRepositoryError() from exc
        return workflow

    def get_by_id(self, workflow_id: UUID) -> CatalogIntelligenceWorkflow | None:
        try:
            items: list[dict[str, Any]] = []
            start: WireItem | None = None
            while True:
                request: dict[str, Any] = {
                    "TableName": self._table_name,
                    "KeyConditionExpression": "#pk=:pk",
                    "ExpressionAttributeNames": {"#pk": "workflowId"},
                    "ExpressionAttributeValues": serialize_item({":pk": workflow_id}),
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
        except CatalogWorkflowRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, TypeError, ValueError) as exc:
            raise CatalogWorkflowRepositoryError() from exc

    def save_state(
        self, workflow: CatalogIntelligenceWorkflow, *, expected_version: int
    ) -> CatalogIntelligenceWorkflow:
        if workflow.version != expected_version + 1:
            raise ValueError("saved workflow version must increment exactly once")
        records = [
            self._meta(workflow),
            *(self._stage(workflow.workflow_id, s) for s in workflow.stages),
        ]
        self._guard_size(*records)
        transaction: list[dict[str, Any]] = [
            {
                "Put": {
                    "TableName": self._table_name,
                    "Item": serialize_item(records[0]),
                    "ConditionExpression": "#version=:expectedVersion",
                    "ExpressionAttributeNames": {"#version": "version"},
                    "ExpressionAttributeValues": serialize_item(
                        {":expectedVersion": expected_version}
                    ),
                }
            },
            *(
                {
                    "Put": {
                        "TableName": self._table_name,
                        "Item": serialize_item(record),
                    }
                }
                for record in records[1:]
            ),
        ]
        if workflow.status in TERMINAL_WORKFLOW_STATUSES:
            transaction.append(
                {
                    "Delete": {
                        "TableName": self._table_name,
                        "Key": serialize_item(
                            {
                                "workflowId": f"ACTIVE_PRODUCT#{workflow.product_id}",
                                "recordKey": "GUARD",
                            }
                        ),
                        "ConditionExpression": "#target=:workflowId",
                        "ExpressionAttributeNames": {"#target": "targetWorkflowId"},
                        "ExpressionAttributeValues": serialize_item(
                            {":workflowId": workflow.workflow_id}
                        ),
                    }
                }
            )
        try:
            self._client.transact_write_items(TransactItems=transaction)
        except ClientError as exc:
            if _error_code(exc) in {
                "TransactionCanceledException",
                "ConditionalCheckFailedException",
            }:
                raise CatalogWorkflowVersionConflictError() from exc
            raise CatalogWorkflowRepositoryError() from exc
        except BotoCoreError as exc:
            raise CatalogWorkflowRepositoryError() from exc
        return workflow

    def list_by_product(
        self, product_id: UUID, *, limit: int = 20, cursor: str | None = None
    ) -> CatalogWorkflowHistoryPage:
        if isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("workflow history limit must be between 1 and 100")
        start = self._decode_cursor(cursor, product_id)
        request: dict[str, Any] = {
            "TableName": self._table_name,
            "IndexName": PRODUCT_CREATED_AT_INDEX,
            "KeyConditionExpression": "#productId=:productId",
            "ExpressionAttributeNames": {"#productId": "productId"},
            "ExpressionAttributeValues": serialize_item({":productId": product_id}),
            "ScanIndexForward": False,
            "Limit": limit,
        }
        if start:
            request["ExclusiveStartKey"] = start
        try:
            response = self._client.query(**request)
            items = tuple(
                self._history(deserialize_item(item))
                for item in cast(list[Mapping[str, AttributeValue]], response.get("Items", []))
            )
            last = cast(WireItem | None, response.get("LastEvaluatedKey"))
            return CatalogWorkflowHistoryPage(
                items=items,
                next_cursor=self._encode_cursor(last, product_id),
            )
        except CatalogWorkflowRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, TypeError, ValueError) as exc:
            raise CatalogWorkflowRepositoryError() from exc

    @staticmethod
    def _meta(workflow: CatalogIntelligenceWorkflow) -> dict[str, Any]:
        return {
            "workflowId": workflow.workflow_id,
            "recordKey": "META",
            "productId": workflow.product_id,
            "productVersion": workflow.product_version,
            "status": workflow.status,
            "version": workflow.version,
            "configuration": workflow.configuration,
            "sourceSnapshot": workflow.source_snapshot,
            "currentStage": workflow.current_stage,
            "progressPercent": workflow.progress_percent,
            "classificationId": workflow.classification_id,
            "extractionId": workflow.extraction_id,
            "normalizationId": workflow.normalization_id,
            "conflictDetectionId": workflow.conflict_detection_id,
            "completenessId": workflow.completeness_id,
            "validationId": workflow.validation_id,
            "selectionId": workflow.selection_id,
            "reviewId": workflow.review_id,
            "materializationId": workflow.materialization_id,
            "projectionId": workflow.projection_id,
            "exportId": workflow.export_id,
            "enrichmentId": workflow.enrichment_id,
            "scoreId": workflow.score_id,
            "createdAt": workflow.created_at,
            "updatedAt": workflow.updated_at,
            "startedAt": workflow.started_at,
            "completedAt": workflow.completed_at,
            "errorCode": workflow.error_code,
            "errorMessage": workflow.error_message,
        }

    @staticmethod
    def _stage(workflow_id: UUID, stage: CatalogIntelligenceWorkflowStage) -> dict[str, Any]:
        return {
            "workflowId": workflow_id,
            "recordKey": f"STAGE#{stage.stage.value}",
            "stage": stage.stage,
            "status": stage.status,
            "jobId": stage.job_id,
            "childJobIds": stage.child_job_ids,
            "resultReference": stage.result_reference,
            "startedAt": stage.started_at,
            "completedAt": stage.completed_at,
            "errorCode": stage.error_code,
            "errorMessage": stage.error_message,
            "skipReason": stage.skip_reason,
        }

    @classmethod
    def _from_items(cls, items: list[dict[str, Any]]) -> CatalogIntelligenceWorkflow:
        meta = next((item for item in items if item.get("recordKey") == "META"), None)
        if meta is None:
            raise CatalogWorkflowRepositoryError("workflow META record is missing")
        stage_items = {
            str(item.get("stage")): item
            for item in items
            if str(item.get("recordKey", "")).startswith("STAGE#")
        }
        if set(stage_items) != {stage.value for stage in CatalogWorkflowStageName}:
            raise CatalogWorkflowRepositoryError("workflow stage records are incomplete")
        config = cast(dict[str, Any], meta["configuration"])
        sources = cast(list[dict[str, Any]], meta["sourceSnapshot"])
        return CatalogIntelligenceWorkflow(
            workflow_id=UUID(str(meta["workflowId"])),
            product_id=UUID(str(meta["productId"])),
            product_version=int(meta["productVersion"]),
            status=CatalogWorkflowStatus(str(meta["status"])),
            version=int(meta["version"]),
            configuration=CatalogIntelligenceWorkflowConfiguration(
                apply_publishing_readiness=bool(config["apply_publishing_readiness"]),
                generate_export=bool(config["generate_export"]),
                generate_ai_enrichment=bool(config["generate_ai_enrichment"]),
                calculate_intelligence_score=bool(config["calculate_intelligence_score"]),
                fail_on_optional_stage_error=bool(config["fail_on_optional_stage_error"]),
            ),
            source_snapshot=tuple(
                CatalogWorkflowSourceSnapshot(
                    source_id=UUID(str(item["source_id"])),
                    source_type=ProductSourceType(str(item["source_type"])),
                )
                for item in sources
            ),
            current_stage=(
                CatalogWorkflowStageName(str(meta["currentStage"]))
                if meta.get("currentStage") is not None
                else None
            ),
            progress_percent=int(meta["progressPercent"]),
            stages=tuple(
                cls._stage_from_item(stage_items[stage.value]) for stage in CatalogWorkflowStageName
            ),
            classification_id=_uuid(meta.get("classificationId")),
            extraction_id=_uuid(meta.get("extractionId")),
            normalization_id=_uuid(meta.get("normalizationId")),
            conflict_detection_id=_uuid(meta.get("conflictDetectionId")),
            completeness_id=_uuid(meta.get("completenessId")),
            validation_id=_uuid(meta.get("validationId")),
            selection_id=_uuid(meta.get("selectionId")),
            review_id=_uuid(meta.get("reviewId")),
            materialization_id=_uuid(meta.get("materializationId")),
            projection_id=_uuid(meta.get("projectionId")),
            export_id=_uuid(meta.get("exportId")),
            enrichment_id=_uuid(meta.get("enrichmentId")),
            score_id=_uuid(meta.get("scoreId")),
            created_at=parse_utc(meta["createdAt"]),
            updated_at=parse_utc(meta["updatedAt"]),
            started_at=parse_utc(meta["startedAt"]) if meta.get("startedAt") else None,
            completed_at=parse_utc(meta["completedAt"]) if meta.get("completedAt") else None,
            error_code=cast(str | None, meta.get("errorCode")),
            error_message=cast(str | None, meta.get("errorMessage")),
        )

    @staticmethod
    def _stage_from_item(item: dict[str, Any]) -> CatalogIntelligenceWorkflowStage:
        return CatalogIntelligenceWorkflowStage(
            stage=CatalogWorkflowStageName(str(item["stage"])),
            status=CatalogWorkflowStageStatus(str(item["status"])),
            job_id=_uuid(item.get("jobId")),
            child_job_ids=tuple(UUID(str(value)) for value in item.get("childJobIds", [])),
            result_reference=cast(str | None, item.get("resultReference")),
            started_at=parse_utc(item["startedAt"]) if item.get("startedAt") else None,
            completed_at=parse_utc(item["completedAt"]) if item.get("completedAt") else None,
            error_code=cast(str | None, item.get("errorCode")),
            error_message=cast(str | None, item.get("errorMessage")),
            skip_reason=cast(str | None, item.get("skipReason")),
        )

    @staticmethod
    def _history(item: dict[str, Any]) -> CatalogWorkflowHistoryItem:
        return CatalogWorkflowHistoryItem(
            workflow_id=UUID(str(item["workflowId"])),
            product_id=UUID(str(item["productId"])),
            status=CatalogWorkflowStatus(str(item["status"])),
            progress_percent=int(item["progressPercent"]),
            current_stage=(
                CatalogWorkflowStageName(str(item["currentStage"]))
                if item.get("currentStage") is not None
                else None
            ),
            created_at=parse_utc(item["createdAt"]),
            completed_at=parse_utc(item["completedAt"]) if item.get("completedAt") else None,
        )

    @staticmethod
    def _encode_cursor(key: WireItem | None, product_id: UUID) -> str | None:
        if not key:
            return None
        payload = json.dumps(
            {"scope": "catalog_workflows", "productId": str(product_id), "key": key},
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        return base64.urlsafe_b64encode(payload).decode().rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str | None, product_id: UUID) -> WireItem | None:
        if cursor is None:
            return None
        if not cursor or len(cursor) > 4_096:
            raise InvalidCatalogWorkflowCursorError()
        try:
            raw = base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
            value = json.loads(raw.decode())
            if (
                not isinstance(value, dict)
                or set(value) != {"scope", "productId", "key"}
                or value["scope"] != "catalog_workflows"
                or value["productId"] != str(product_id)
                or not isinstance(value["key"], dict)
                or not value["key"]
            ):
                raise ValueError
            return cast(WireItem, value["key"])
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise InvalidCatalogWorkflowCursorError() from exc

    @staticmethod
    def _guard_size(*items: dict[str, Any]) -> None:
        if any(
            len(json.dumps(serialize_item(item), default=str, separators=(",", ":")).encode())
            > MAX_SAFE_ITEM_BYTES
            for item in items
        ):
            raise CatalogWorkflowRepositoryError("workflow record exceeds safe item size")


def _uuid(value: object) -> UUID | None:
    return UUID(str(value)) if value is not None else None


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))
