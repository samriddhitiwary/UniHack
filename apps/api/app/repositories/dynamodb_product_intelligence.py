"""Immutable DynamoDB Product Intelligence Score persistence."""

import base64
import hashlib
import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    ProductIntelligenceAlreadyExistsError,
    ProductIntelligenceResultItemTooLargeError,
    ProductIntelligenceScoreRepositoryError,
    ProductIntelligenceScoreSerializationError,
)
from app.domain.catalog_projection import CatalogProjectionStatus
from app.domain.product_intelligence import (
    ComponentEvaluationStatus,
    ProductIntelligenceComponent,
    ProductIntelligenceComponentScore,
    ProductIntelligenceGrade,
    ProductIntelligenceMetric,
    ProductIntelligenceScorePage,
    ProductIntelligenceScoreResult,
)
from app.domain.products import ProductCategory
from app.utils.dynamodb import AttributeValue, deserialize_item, parse_utc, serialize_item

JOB_ID_INDEX = "JobIdIndex"
PRODUCT_CREATED_AT_INDEX = "ProductCreatedAtIndex"
PROJECTION_ID_INDEX = "ProjectionIdIndex"
MAX_SAFE_ITEM_BYTES = 390_000


def product_intelligence_input_key(
    projection_id: UUID, enrichment_id: UUID | None, policy_version: str
) -> str:
    raw = f"{projection_id}|{enrichment_id or 'NONE'}|{policy_version}".encode()
    return hashlib.sha256(raw).hexdigest()


class DynamoDBProductIntelligenceScoreRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client, self._table_name = client, table_name

    def create(self, result: ProductIntelligenceScoreResult) -> ProductIntelligenceScoreResult:
        input_key = product_intelligence_input_key(
            result.projection_id, result.enrichment_id, result.policy_version
        )
        records = [
            self._meta(result, input_key),
            *(self._component(result.score_id, item) for item in result.components),
        ]
        guard = {
            "scoreId": f"SCORE_INPUT#{input_key}",
            "recordKey": "GUARD",
            "targetScoreId": result.score_id,
        }
        self._guard_size(guard, *records)
        try:
            self._client.transact_write_items(
                TransactItems=[self._put(guard), *(self._put(item) for item in records)]
            )
        except ClientError as exc:
            if str(exc.response.get("Error", {}).get("Code", "")) in {
                "TransactionCanceledException",
                "ConditionalCheckFailedException",
            }:
                raise ProductIntelligenceAlreadyExistsError() from exc
            raise ProductIntelligenceScoreRepositoryError() from exc
        except BotoCoreError as exc:
            raise ProductIntelligenceScoreRepositoryError() from exc
        return result

    def get_by_id(self, score_id: UUID) -> ProductIntelligenceScoreResult | None:
        try:
            response = self._client.query(
                TableName=self._table_name,
                KeyConditionExpression="#id=:id",
                ExpressionAttributeNames={"#id": "scoreId"},
                ExpressionAttributeValues=serialize_item({":id": score_id}),
                ConsistentRead=True,
            )
            items = [
                deserialize_item(item)
                for item in cast(list[Mapping[str, AttributeValue]], response.get("Items", []))
            ]
            return self._from_items(items) if items else None
        except ProductIntelligenceScoreSerializationError:
            raise
        except (BotoCoreError, ClientError, KeyError, TypeError, ValueError) as exc:
            raise ProductIntelligenceScoreRepositoryError() from exc

    def get_by_job_id(self, job_id: UUID) -> ProductIntelligenceScoreResult | None:
        results = self._query_meta(JOB_ID_INDEX, "jobId", job_id, 1)
        return results[0] if results else None

    def get_by_input_key(self, input_key: str) -> ProductIntelligenceScoreResult | None:
        try:
            response = self._client.get_item(
                TableName=self._table_name,
                Key=serialize_item({"scoreId": f"SCORE_INPUT#{input_key}", "recordKey": "GUARD"}),
                ConsistentRead=True,
            )
            item = response.get("Item")
            return (
                self.get_by_id(
                    UUID(
                        str(
                            deserialize_item(cast(Mapping[str, AttributeValue], item))[
                                "targetScoreId"
                            ]
                        )
                    )
                )
                if item
                else None
            )
        except ProductIntelligenceScoreRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, TypeError, ValueError) as exc:
            raise ProductIntelligenceScoreRepositoryError() from exc

    def get_by_projection_id(
        self, projection_id: UUID
    ) -> tuple[ProductIntelligenceScoreResult, ...]:
        return self._query_meta(PROJECTION_ID_INDEX, "projectionId", projection_id, 100)

    def list_by_product(
        self, product_id: UUID, *, limit: int, cursor: str | None = None
    ) -> ProductIntelligenceScorePage:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        request: dict[str, Any] = {
            "TableName": self._table_name,
            "IndexName": PRODUCT_CREATED_AT_INDEX,
            "KeyConditionExpression": "#key=:value",
            "ExpressionAttributeNames": {"#key": "productId"},
            "ExpressionAttributeValues": serialize_item({":value": product_id}),
            "ScanIndexForward": False,
            "Limit": limit,
        }
        if cursor:
            request["ExclusiveStartKey"] = serialize_item(self._decode_cursor(cursor, product_id))
        try:
            response = self._client.query(**request)
            metas = [
                deserialize_item(item)
                for item in cast(list[Mapping[str, AttributeValue]], response.get("Items", []))
            ]
            results = tuple(self.get_by_id(UUID(str(item["scoreId"]))) for item in metas)
            if any(item is None for item in results):
                raise ProductIntelligenceScoreSerializationError()
            last = response.get("LastEvaluatedKey")
            next_cursor = (
                self._encode_cursor(
                    deserialize_item(cast(Mapping[str, AttributeValue], last)), product_id
                )
                if last
                else None
            )
            return ProductIntelligenceScorePage(
                cast(tuple[ProductIntelligenceScoreResult, ...], results), next_cursor
            )
        except ProductIntelligenceScoreRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, TypeError, ValueError) as exc:
            raise ProductIntelligenceScoreRepositoryError() from exc

    def _query_meta(
        self, index: str, key: str, value: UUID, limit: int
    ) -> tuple[ProductIntelligenceScoreResult, ...]:
        try:
            response = self._client.query(
                TableName=self._table_name,
                IndexName=index,
                KeyConditionExpression="#key=:value",
                ExpressionAttributeNames={"#key": key},
                ExpressionAttributeValues=serialize_item({":value": value}),
                ScanIndexForward=False,
                Limit=limit,
            )
            values = tuple(
                self.get_by_id(UUID(str(deserialize_item(item)["scoreId"])))
                for item in cast(list[Mapping[str, AttributeValue]], response.get("Items", []))
            )
            if any(item is None for item in values):
                raise ProductIntelligenceScoreSerializationError()
            return cast(tuple[ProductIntelligenceScoreResult, ...], values)
        except ProductIntelligenceScoreRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, TypeError, ValueError) as exc:
            raise ProductIntelligenceScoreRepositoryError() from exc

    @staticmethod
    def _meta(result: ProductIntelligenceScoreResult, input_key: str) -> dict[str, Any]:
        return {
            "scoreId": result.score_id,
            "recordKey": "META",
            "inputKey": input_key,
            "jobId": result.job_id,
            "productId": result.product_id,
            "projectionId": result.projection_id,
            "materializationId": result.materialization_id,
            "reviewId": result.review_id,
            "selectionId": result.selection_id,
            "validationId": result.validation_id,
            "completenessId": result.completeness_id,
            "conflictDetectionId": result.conflict_detection_id,
            "normalizationId": result.normalization_id,
            "extractionId": result.extraction_id,
            "classificationId": result.classification_id,
            "enrichmentId": result.enrichment_id,
            "category": result.category,
            "schemaVersion": result.schema_version,
            "schemaFingerprint": result.schema_fingerprint,
            "projectionStatus": result.projection_status,
            "overallScoreBp": result.overall_score_bp,
            "overallScorePercent": result.overall_score_percent,
            "grade": result.grade,
            "strengthCodes": result.strength_codes,
            "improvementCodes": result.improvement_codes,
            "topImprovementCodes": result.top_improvement_codes,
            "metrics": {item.name: item.value for item in result.metrics},
            "policyVersion": result.policy_version,
            "engine": result.engine,
            "engineVersion": result.engine_version,
            "createdAt": result.created_at,
        }

    @staticmethod
    def _component(score_id: UUID, item: ProductIntelligenceComponentScore) -> dict[str, Any]:
        return {
            "scoreId": score_id,
            "recordKey": f"COMPONENT#{item.component.value}",
            "component": item.component,
            "status": item.status,
            "rawScoreBp": item.raw_score_bp,
            "baseWeightBp": item.base_weight_bp,
            "normalizedWeightBp": item.normalized_weight_bp,
            "weightedContributionBp": item.weighted_contribution_bp,
            "strengthCodes": item.strength_codes,
            "improvementCodes": item.improvement_codes,
            "metrics": {metric.name: metric.value for metric in item.metrics},
        }

    @staticmethod
    def _from_items(items: list[dict[str, Any]]) -> ProductIntelligenceScoreResult:
        try:
            meta = next(item for item in items if item["recordKey"] == "META")
            records = {
                str(item["component"]): item
                for item in items
                if str(item["recordKey"]).startswith("COMPONENT#")
            }
            if set(records) != {item.value for item in ProductIntelligenceComponent}:
                raise ProductIntelligenceScoreSerializationError()
            components = tuple(
                ProductIntelligenceComponentScore(
                    component=component,
                    status=ComponentEvaluationStatus(str(records[component.value]["status"])),
                    raw_score_bp=int(records[component.value]["rawScoreBp"])
                    if records[component.value].get("rawScoreBp") is not None
                    else None,
                    base_weight_bp=int(records[component.value]["baseWeightBp"]),
                    normalized_weight_bp=int(records[component.value]["normalizedWeightBp"]),
                    weighted_contribution_bp=int(
                        records[component.value]["weightedContributionBp"]
                    ),
                    strength_codes=tuple(str(v) for v in records[component.value]["strengthCodes"]),
                    improvement_codes=tuple(
                        str(v) for v in records[component.value]["improvementCodes"]
                    ),
                    metrics=tuple(
                        ProductIntelligenceMetric(name=str(k), value=int(v))
                        for k, v in records[component.value]["metrics"].items()
                    ),
                )
                for component in ProductIntelligenceComponent
            )
            return ProductIntelligenceScoreResult(
                score_id=UUID(str(meta["scoreId"])),
                job_id=UUID(str(meta["jobId"])),
                product_id=UUID(str(meta["productId"])),
                projection_id=UUID(str(meta["projectionId"])),
                materialization_id=UUID(str(meta["materializationId"])),
                review_id=UUID(str(meta["reviewId"])),
                selection_id=UUID(str(meta["selectionId"])),
                validation_id=UUID(str(meta["validationId"])),
                completeness_id=UUID(str(meta["completenessId"])),
                conflict_detection_id=UUID(str(meta["conflictDetectionId"])),
                normalization_id=UUID(str(meta["normalizationId"])),
                extraction_id=UUID(str(meta["extractionId"])),
                classification_id=UUID(str(meta["classificationId"])),
                enrichment_id=UUID(str(meta["enrichmentId"])) if meta.get("enrichmentId") else None,
                category=ProductCategory(str(meta["category"])),
                schema_version=int(meta["schemaVersion"]),
                schema_fingerprint=str(meta["schemaFingerprint"]),
                projection_status=CatalogProjectionStatus(str(meta["projectionStatus"])),
                overall_score_bp=int(meta["overallScoreBp"]),
                overall_score_percent=int(meta["overallScorePercent"]),
                grade=ProductIntelligenceGrade(str(meta["grade"])),
                components=components,
                strength_codes=tuple(str(v) for v in meta["strengthCodes"]),
                improvement_codes=tuple(str(v) for v in meta["improvementCodes"]),
                top_improvement_codes=tuple(str(v) for v in meta["topImprovementCodes"]),
                metrics=tuple(
                    ProductIntelligenceMetric(name=str(k), value=int(v))
                    for k, v in meta["metrics"].items()
                ),
                policy_version=str(meta["policyVersion"]),
                engine=str(meta["engine"]),
                engine_version=str(meta["engineVersion"]),
                created_at=parse_utc(meta["createdAt"]),
            )
        except ProductIntelligenceScoreSerializationError:
            raise
        except (KeyError, StopIteration, TypeError, ValueError) as exc:
            raise ProductIntelligenceScoreSerializationError() from exc

    def _put(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "Put": {
                "TableName": self._table_name,
                "Item": serialize_item(item),
                "ConditionExpression": "attribute_not_exists(#pk)",
                "ExpressionAttributeNames": {"#pk": "scoreId"},
            }
        }

    @staticmethod
    def _guard_size(*items: dict[str, Any]) -> None:
        if any(
            len(json.dumps(serialize_item(item), separators=(",", ":"), default=str).encode())
            > MAX_SAFE_ITEM_BYTES
            for item in items
        ):
            raise ProductIntelligenceResultItemTooLargeError()

    @staticmethod
    def _encode_cursor(key: dict[str, Any], product_id: UUID) -> str:
        payload = {"p": str(product_id), "k": key}
        return (
            base64.urlsafe_b64encode(
                json.dumps(payload, separators=(",", ":"), default=str).encode()
            )
            .decode()
            .rstrip("=")
        )

    @staticmethod
    def _decode_cursor(cursor: str, product_id: UUID) -> dict[str, Any]:
        try:
            payload = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
            if payload["p"] != str(product_id) or not isinstance(payload["k"], dict):
                raise ValueError
            return cast(dict[str, Any], payload["k"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("invalid Product Intelligence Score cursor") from exc
