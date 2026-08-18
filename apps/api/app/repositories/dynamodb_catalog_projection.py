"""Immutable DynamoDB persistence for commerce catalog projections."""

import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    CatalogProjectionAlreadyExistsError,
    CatalogProjectionRepositoryError,
    CatalogProjectionResultItemTooLargeError,
    CatalogProjectionSerializationError,
)
from app.domain.attribute_validation import CandidateValidationStatus
from app.domain.catalog_projection import (
    CatalogBlockingReason,
    CatalogProjectionStatus,
    CatalogWarningReason,
    CommerceCatalogAttribute,
    CommerceCatalogProjection,
)
from app.domain.category_schemas import AttributeDataType
from app.domain.products import ProductCategory
from app.domain.reviewed_attributes import FinalAttributeOrigin
from app.utils.dynamodb import AttributeValue, WireItem, deserialize_item, parse_utc, serialize_item

JOB_ID_INDEX = "JobIdIndex"
MATERIALIZATION_ID_INDEX = "MaterializationIdIndex"
MAX_SAFE_ITEM_BYTES = 390_000


class DynamoDBCommerceCatalogProjectionRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client, self._table_name = client, table_name

    def create(self, result: CommerceCatalogProjection) -> CommerceCatalogProjection:
        meta = self._meta(result)
        guard = {
            "projectionId": f"MATERIALIZATION#{result.materialization_id}",
            "recordKey": "CATALOG_PROJECTION",
            "targetProjectionId": result.projection_id,
        }
        attributes = [
            self._attribute(result.projection_id, index, value)
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
                            "ExpressionAttributeNames": {"#pk": "projectionId"},
                        }
                    },
                    {
                        "Put": {
                            "TableName": self._table_name,
                            "Item": serialize_item(guard),
                            "ConditionExpression": "attribute_not_exists(#pk)",
                            "ExpressionAttributeNames": {"#pk": "projectionId"},
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
                raise CatalogProjectionAlreadyExistsError() from exc
            raise CatalogProjectionRepositoryError() from exc
        except BotoCoreError as exc:
            raise CatalogProjectionRepositoryError() from exc
        return result

    def get_by_id(self, projection_id: UUID) -> CommerceCatalogProjection | None:
        items: list[dict[str, Any]] = []
        start: WireItem | None = None
        try:
            while True:
                request: dict[str, Any] = {
                    "TableName": self._table_name,
                    "KeyConditionExpression": "#id=:id",
                    "ExpressionAttributeNames": {"#id": "projectionId"},
                    "ExpressionAttributeValues": serialize_item({":id": projection_id}),
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
        except CatalogProjectionSerializationError:
            raise
        except (BotoCoreError, ClientError, KeyError, ValueError, TypeError) as exc:
            raise CatalogProjectionRepositoryError() from exc

    def get_by_job_id(self, job_id: UUID) -> CommerceCatalogProjection | None:
        return self._get_by_index(JOB_ID_INDEX, "jobId", job_id)

    def get_by_materialization_id(
        self, materialization_id: UUID
    ) -> CommerceCatalogProjection | None:
        return self._get_by_index(MATERIALIZATION_ID_INDEX, "materializationId", materialization_id)

    def _get_by_index(self, index: str, key: str, value: UUID) -> CommerceCatalogProjection | None:
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
                else self.get_by_id(UUID(str(deserialize_item(items[0])["projectionId"])))
            )
        except CatalogProjectionRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, ValueError, TypeError) as exc:
            raise CatalogProjectionRepositoryError() from exc

    @staticmethod
    def _meta(result: CommerceCatalogProjection) -> dict[str, Any]:
        return {
            "projectionId": result.projection_id,
            "recordKey": "META",
            "jobId": result.job_id,
            "productId": result.product_id,
            "productVersion": result.product_version,
            "materializationId": result.materialization_id,
            "reviewId": result.review_id,
            "selectionId": result.selection_id,
            "validationId": result.validation_id,
            "completenessId": result.completeness_id,
            "conflictDetectionId": result.conflict_detection_id,
            "normalizationId": result.normalization_id,
            "extractionId": result.extraction_id,
            "classificationId": result.classification_id,
            "category": result.category,
            "schemaVersion": result.schema_version,
            "schemaFingerprint": result.schema_fingerprint,
            "productName": result.product_name,
            "manufacturer": result.manufacturer,
            "modelNumber": result.model_number,
            "description": result.description,
            "status": result.status,
            "attributeCount": result.attribute_count,
            "requiredAttributeCount": result.required_attribute_count,
            "optionalAttributeCount": result.optional_attribute_count,
            "unresolvedOptionalCount": result.unresolved_optional_count,
            "blockingReasonCodes": result.blocking_reason_codes,
            "warningReasonCodes": result.warning_reason_codes,
            "engine": result.engine,
            "engineVersion": result.engine_version,
            "createdAt": result.created_at,
        }

    @staticmethod
    def _attribute(
        projection_id: UUID, index: int, value: CommerceCatalogAttribute
    ) -> dict[str, Any]:
        return {
            "projectionId": projection_id,
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
            "candidateId": value.candidate_id,
            "sourceId": value.source_id,
            "validationStatus": value.validation_status,
            "createdAt": value.created_at,
        }

    @staticmethod
    def _from_items(items: list[dict[str, Any]]) -> CommerceCatalogProjection:
        try:
            meta = next(item for item in items if item["recordKey"] == "META")
            records = sorted(
                (item for item in items if str(item["recordKey"]).startswith("ATTRIBUTE#")),
                key=lambda item: str(item["recordKey"]),
            )
            attributes = tuple(
                CommerceCatalogAttribute(
                    attribute_name=str(item["attributeName"]),
                    attribute_display_name=str(item["attributeDisplayName"]),
                    data_type=AttributeDataType(str(item["dataType"])),
                    required=bool(item["required"]),
                    display_order=int(item["displayOrder"]),
                    value=str(item["value"]),
                    unit=None if item.get("unit") is None else str(item["unit"]),
                    origin=FinalAttributeOrigin(str(item["origin"])),
                    review_decision_id=UUID(str(item["reviewDecisionId"])),
                    candidate_id=None
                    if item.get("candidateId") is None
                    else str(item["candidateId"]),
                    source_id=None if item.get("sourceId") is None else UUID(str(item["sourceId"])),
                    validation_status=None
                    if item.get("validationStatus") is None
                    else CandidateValidationStatus(str(item["validationStatus"])),
                    created_at=parse_utc(item["createdAt"]),
                )
                for item in records
            )
            if len(attributes) != int(meta["attributeCount"]):
                raise CatalogProjectionSerializationError()
            return CommerceCatalogProjection(
                projection_id=UUID(str(meta["projectionId"])),
                job_id=UUID(str(meta["jobId"])),
                product_id=UUID(str(meta["productId"])),
                product_version=int(meta["productVersion"]),
                materialization_id=UUID(str(meta["materializationId"])),
                review_id=UUID(str(meta["reviewId"])),
                selection_id=UUID(str(meta["selectionId"])),
                validation_id=UUID(str(meta["validationId"])),
                completeness_id=UUID(str(meta["completenessId"])),
                conflict_detection_id=UUID(str(meta["conflictDetectionId"])),
                normalization_id=UUID(str(meta["normalizationId"])),
                extraction_id=UUID(str(meta["extractionId"])),
                classification_id=UUID(str(meta["classificationId"])),
                category=ProductCategory(str(meta["category"])),
                schema_version=int(meta["schemaVersion"]),
                schema_fingerprint=str(meta["schemaFingerprint"]),
                product_name=str(meta["productName"]),
                manufacturer=None
                if meta.get("manufacturer") is None
                else str(meta["manufacturer"]),
                model_number=None if meta.get("modelNumber") is None else str(meta["modelNumber"]),
                description=None if meta.get("description") is None else str(meta["description"]),
                status=CatalogProjectionStatus(str(meta["status"])),
                attribute_count=int(meta["attributeCount"]),
                required_attribute_count=int(meta["requiredAttributeCount"]),
                optional_attribute_count=int(meta["optionalAttributeCount"]),
                unresolved_optional_count=int(meta["unresolvedOptionalCount"]),
                blocking_reason_codes=tuple(
                    CatalogBlockingReason(str(value)) for value in meta["blockingReasonCodes"]
                ),
                warning_reason_codes=tuple(
                    CatalogWarningReason(str(value)) for value in meta["warningReasonCodes"]
                ),
                attributes=attributes,
                engine=str(meta["engine"]),
                engine_version=str(meta["engineVersion"]),
                created_at=parse_utc(meta["createdAt"]),
            )
        except CatalogProjectionSerializationError:
            raise
        except (KeyError, ValueError, TypeError, StopIteration) as exc:
            raise CatalogProjectionSerializationError() from exc

    @staticmethod
    def _guard_size(*items: dict[str, Any]) -> None:
        if any(
            len(json.dumps(serialize_item(item), separators=(",", ":"), default=str).encode())
            > MAX_SAFE_ITEM_BYTES
            for item in items
        ):
            raise CatalogProjectionResultItemTooLargeError()

    @staticmethod
    def _code(exc: ClientError) -> str:
        return str(exc.response.get("Error", {}).get("Code", ""))
