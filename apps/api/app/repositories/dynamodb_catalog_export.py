"""Immutable DynamoDB persistence for catalog export result metadata."""

import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    CatalogExportAlreadyExistsError,
    CatalogExportRepositoryError,
    CatalogExportResultItemTooLargeError,
    CatalogExportResultSerializationError,
)
from app.domain.catalog_export import (
    CatalogExportArtifact,
    CatalogExportArtifactFormat,
    CatalogExportResult,
    CatalogExportStatus,
)
from app.domain.catalog_projection import CatalogProjectionStatus, CatalogWarningReason
from app.domain.products import ProductCategory
from app.utils.dynamodb import AttributeValue, WireItem, deserialize_item, parse_utc, serialize_item

JOB_ID_INDEX = "JobIdIndex"
PROJECTION_ID_INDEX = "ProjectionIdIndex"
MAX_SAFE_ITEM_BYTES = 390_000


class DynamoDBCatalogExportResultRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client = client
        self._table_name = table_name

    def create(self, result: CatalogExportResult) -> CatalogExportResult:
        meta = self._meta(result)
        guard = {
            "exportId": f"PROJECTION#{result.projection_id}",
            "recordKey": "CATALOG_EXPORT",
            "targetExportId": result.export_id,
        }
        artifacts = [self._artifact(result.export_id, item) for item in result.artifacts]
        self._guard_size(meta, guard, *artifacts)
        try:
            self._client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self._table_name,
                            "Item": serialize_item(meta),
                            "ConditionExpression": "attribute_not_exists(#pk)",
                            "ExpressionAttributeNames": {"#pk": "exportId"},
                        }
                    },
                    {
                        "Put": {
                            "TableName": self._table_name,
                            "Item": serialize_item(guard),
                            "ConditionExpression": "attribute_not_exists(#pk)",
                            "ExpressionAttributeNames": {"#pk": "exportId"},
                        }
                    },
                ]
            )
            for item in artifacts:
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
                raise CatalogExportAlreadyExistsError() from exc
            raise CatalogExportRepositoryError() from exc
        except BotoCoreError as exc:
            raise CatalogExportRepositoryError() from exc
        return result

    def get_by_id(self, export_id: UUID) -> CatalogExportResult | None:
        items: list[dict[str, Any]] = []
        start: WireItem | None = None
        try:
            while True:
                request: dict[str, Any] = {
                    "TableName": self._table_name,
                    "KeyConditionExpression": "#id=:id",
                    "ExpressionAttributeNames": {"#id": "exportId"},
                    "ExpressionAttributeValues": serialize_item({":id": export_id}),
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
        except CatalogExportResultSerializationError:
            raise
        except (BotoCoreError, ClientError, KeyError, TypeError, ValueError) as exc:
            raise CatalogExportRepositoryError() from exc

    def get_by_job_id(self, job_id: UUID) -> CatalogExportResult | None:
        return self._get_by_index(JOB_ID_INDEX, "jobId", job_id)

    def get_by_projection_id(self, projection_id: UUID) -> CatalogExportResult | None:
        return self._get_by_index(PROJECTION_ID_INDEX, "projectionId", projection_id)

    def _get_by_index(self, index: str, key: str, value: UUID) -> CatalogExportResult | None:
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
                else self.get_by_id(UUID(str(deserialize_item(items[0])["exportId"])))
            )
        except CatalogExportResultSerializationError:
            raise
        except CatalogExportRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, TypeError, ValueError) as exc:
            raise CatalogExportRepositoryError() from exc

    @staticmethod
    def _meta(result: CatalogExportResult) -> dict[str, Any]:
        return {
            "exportId": result.export_id,
            "recordKey": "META",
            "jobId": result.job_id,
            "productId": result.product_id,
            "projectionId": result.projection_id,
            "projectionProductVersion": result.projection_product_version,
            "category": result.category,
            "schemaVersion": result.schema_version,
            "schemaFingerprint": result.schema_fingerprint,
            "projectionStatus": result.projection_status,
            "status": result.status,
            "artifactCount": len(result.artifacts),
            "warningReasonCodes": result.warning_reason_codes,
            "engine": result.engine,
            "engineVersion": result.engine_version,
            "createdAt": result.created_at,
        }

    @staticmethod
    def _artifact(export_id: UUID, item: CatalogExportArtifact) -> dict[str, Any]:
        return {
            "exportId": export_id,
            "recordKey": f"ARTIFACT#{item.format.value}",
            "format": item.format,
            "fileName": item.file_name,
            "mediaType": item.media_type,
            "objectKey": item.object_key,
            "sizeBytes": item.size_bytes,
            "sha256": item.sha256,
            "createdAt": item.created_at,
        }

    @staticmethod
    def _from_items(items: list[dict[str, Any]]) -> CatalogExportResult:
        try:
            meta = next(item for item in items if item["recordKey"] == "META")
            records = {
                CatalogExportArtifactFormat(str(item["format"])): item
                for item in items
                if str(item["recordKey"]).startswith("ARTIFACT#")
            }
            if len(records) != int(meta["artifactCount"]) or len(records) != 3:
                raise CatalogExportResultSerializationError()
            artifacts = tuple(
                CatalogExportArtifact(
                    format=format,
                    file_name=str(records[format]["fileName"]),
                    media_type=str(records[format]["mediaType"]),
                    object_key=str(records[format]["objectKey"]),
                    size_bytes=int(records[format]["sizeBytes"]),
                    sha256=str(records[format]["sha256"]),
                    created_at=parse_utc(records[format]["createdAt"]),
                )
                for format in CatalogExportArtifactFormat
            )
            return CatalogExportResult(
                export_id=UUID(str(meta["exportId"])),
                job_id=UUID(str(meta["jobId"])),
                product_id=UUID(str(meta["productId"])),
                projection_id=UUID(str(meta["projectionId"])),
                projection_product_version=int(meta["projectionProductVersion"]),
                category=ProductCategory(str(meta["category"])),
                schema_version=int(meta["schemaVersion"]),
                schema_fingerprint=str(meta["schemaFingerprint"]),
                projection_status=CatalogProjectionStatus(str(meta["projectionStatus"])),
                status=CatalogExportStatus(str(meta["status"])),
                artifacts=artifacts,
                warning_reason_codes=tuple(
                    CatalogWarningReason(str(value)) for value in meta["warningReasonCodes"]
                ),
                engine=str(meta["engine"]),
                engine_version=str(meta["engineVersion"]),
                created_at=parse_utc(meta["createdAt"]),
            )
        except CatalogExportResultSerializationError:
            raise
        except (KeyError, TypeError, ValueError, StopIteration) as exc:
            raise CatalogExportResultSerializationError() from exc

    @staticmethod
    def _guard_size(*items: dict[str, Any]) -> None:
        if any(
            len(json.dumps(serialize_item(item), separators=(",", ":"), default=str).encode())
            > MAX_SAFE_ITEM_BYTES
            for item in items
        ):
            raise CatalogExportResultItemTooLargeError()

    @staticmethod
    def _code(exc: ClientError) -> str:
        return str(exc.response.get("Error", {}).get("Code", ""))
