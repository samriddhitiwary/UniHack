"""Immutable DynamoDB persistence for grounded catalog enrichment results."""

import hashlib
import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    CatalogEnrichmentAlreadyExistsError,
    CatalogEnrichmentRepositoryError,
    CatalogEnrichmentResultItemTooLargeError,
    CatalogEnrichmentResultSerializationError,
)
from app.domain.catalog_enrichment import (
    CatalogEnrichmentResult,
    EnrichmentWarningCode,
    GroundedGeneratedText,
)
from app.domain.products import ProductCategory
from app.utils.dynamodb import AttributeValue, WireItem, deserialize_item, parse_utc, serialize_item

JOB_ID_INDEX = "JobIdIndex"
PROJECTION_ID_INDEX = "ProjectionIdIndex"
MAX_SAFE_ITEM_BYTES = 390_000


def enrichment_input_hash(
    *, projection_id: UUID, prompt_version: str, provider: str, model: str
) -> str:
    value = f"{projection_id}|{prompt_version}|{provider}|{model}".encode()
    return hashlib.sha256(value).hexdigest()


class DynamoDBCatalogEnrichmentResultRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client = client
        self._table_name = table_name

    def create(self, result: CatalogEnrichmentResult) -> CatalogEnrichmentResult:
        meta = self._meta(result)
        guard_hash = enrichment_input_hash(
            projection_id=result.projection_id,
            prompt_version=result.prompt_version,
            provider=result.provider,
            model=result.model,
        )
        guard = {
            "enrichmentId": f"ENRICHMENT_INPUT#{guard_hash}",
            "recordKey": "RESULT",
            "targetEnrichmentId": result.enrichment_id,
        }
        content = self._content_records(result)
        self._guard_size(meta, guard, *content)
        try:
            self._client.transact_write_items(
                TransactItems=[
                    self._conditional_put(meta, "#pk", "enrichmentId"),
                    self._conditional_put(guard, "#pk", "enrichmentId"),
                ]
            )
            for item in content:
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
                raise CatalogEnrichmentAlreadyExistsError() from exc
            raise CatalogEnrichmentRepositoryError() from exc
        except BotoCoreError as exc:
            raise CatalogEnrichmentRepositoryError() from exc
        return result

    def get_by_id(self, enrichment_id: UUID) -> CatalogEnrichmentResult | None:
        items: list[dict[str, Any]] = []
        start: WireItem | None = None
        try:
            while True:
                request: dict[str, Any] = {
                    "TableName": self._table_name,
                    "KeyConditionExpression": "#id=:id",
                    "ExpressionAttributeNames": {"#id": "enrichmentId"},
                    "ExpressionAttributeValues": serialize_item({":id": enrichment_id}),
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
        except CatalogEnrichmentResultSerializationError:
            raise
        except (BotoCoreError, ClientError, KeyError, TypeError, ValueError) as exc:
            raise CatalogEnrichmentRepositoryError() from exc

    def get_by_job_id(self, job_id: UUID) -> CatalogEnrichmentResult | None:
        results = self._query_index(JOB_ID_INDEX, "jobId", job_id, 1)
        return results[0] if results else None

    def get_by_projection_id(self, projection_id: UUID) -> tuple[CatalogEnrichmentResult, ...]:
        return self._query_index(PROJECTION_ID_INDEX, "projectionId", projection_id, 100)

    def exists_for_projection(self, projection_id: UUID) -> bool:
        try:
            response = self._client.query(
                TableName=self._table_name,
                IndexName=PROJECTION_ID_INDEX,
                KeyConditionExpression="#key=:value",
                ExpressionAttributeNames={"#key": "projectionId"},
                ExpressionAttributeValues=serialize_item({":value": projection_id}),
                ScanIndexForward=False,
                Limit=1,
                Select="COUNT",
            )
            return int(response.get("Count", 0)) > 0
        except (BotoCoreError, ClientError, KeyError, TypeError, ValueError) as exc:
            raise CatalogEnrichmentRepositoryError() from exc

    def _query_index(
        self, index: str, key: str, value: UUID, limit: int
    ) -> tuple[CatalogEnrichmentResult, ...]:
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
            identifiers = [
                UUID(str(deserialize_item(item)["enrichmentId"]))
                for item in cast(list[Mapping[str, AttributeValue]], response.get("Items", []))
            ]
            results = tuple(self.get_by_id(identifier) for identifier in identifiers)
            if any(result is None for result in results):
                raise CatalogEnrichmentResultSerializationError()
            return cast(tuple[CatalogEnrichmentResult, ...], results)
        except CatalogEnrichmentResultSerializationError:
            raise
        except CatalogEnrichmentRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, TypeError, ValueError) as exc:
            raise CatalogEnrichmentRepositoryError() from exc

    @staticmethod
    def _meta(result: CatalogEnrichmentResult) -> dict[str, Any]:
        return {
            "enrichmentId": result.enrichment_id,
            "recordKey": "META",
            "jobId": result.job_id,
            "productId": result.product_id,
            "projectionId": result.projection_id,
            "projectionProductVersion": result.projection_product_version,
            "category": result.category,
            "schemaVersion": result.schema_version,
            "schemaFingerprint": result.schema_fingerprint,
            "bulletCount": len(result.feature_bullets),
            "keywordCount": len(result.search_keywords),
            "trustedFactCount": result.trusted_fact_count,
            "referencedFactCount": result.referenced_fact_count,
            "factCoverageBp": result.fact_coverage_bp,
            "groundingScoreBp": result.grounding_score_bp,
            "warningCodes": result.warning_codes,
            "provider": result.provider,
            "model": result.model,
            "promptVersion": result.prompt_version,
            "promptSha256": result.prompt_sha256,
            "generationAttemptCount": result.generation_attempt_count,
            "engine": result.engine,
            "engineVersion": result.engine_version,
            "createdAt": result.created_at,
        }

    @classmethod
    def _content_records(cls, result: CatalogEnrichmentResult) -> list[dict[str, Any]]:
        records = [
            cls._content(result.enrichment_id, "TITLE", result.title),
            cls._content(result.enrichment_id, "DESCRIPTION", result.description),
            cls._content(result.enrichment_id, "TECHNICAL_SUMMARY", result.technical_summary),
        ]
        records.extend(
            cls._content(result.enrichment_id, f"BULLET#{index:06d}", item, index)
            for index, item in enumerate(result.feature_bullets, 1)
        )
        records.extend(
            cls._content(result.enrichment_id, f"KEYWORD#{index:06d}", item, index)
            for index, item in enumerate(result.search_keywords, 1)
        )
        return records

    @staticmethod
    def _content(
        enrichment_id: UUID,
        record_key: str,
        item: GroundedGeneratedText,
        sequence: int | None = None,
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "enrichmentId": enrichment_id,
            "recordKey": record_key,
            "text": item.text,
            "factIds": item.fact_ids,
        }
        if sequence is not None:
            record["sequence"] = sequence
        return record

    @staticmethod
    def _from_items(items: list[dict[str, Any]]) -> CatalogEnrichmentResult:
        try:
            meta = next(item for item in items if item["recordKey"] == "META")
            records = {
                str(item["recordKey"]): item for item in items if item["recordKey"] != "META"
            }
            required = {"TITLE", "DESCRIPTION", "TECHNICAL_SUMMARY"}
            if not required.issubset(records):
                raise CatalogEnrichmentResultSerializationError()
            bullets = DynamoDBCatalogEnrichmentResultRepository._ordered(
                records, "BULLET#", int(meta["bulletCount"])
            )
            keywords = DynamoDBCatalogEnrichmentResultRepository._ordered(
                records, "KEYWORD#", int(meta["keywordCount"])
            )
            return CatalogEnrichmentResult(
                enrichment_id=UUID(str(meta["enrichmentId"])),
                job_id=UUID(str(meta["jobId"])),
                product_id=UUID(str(meta["productId"])),
                projection_id=UUID(str(meta["projectionId"])),
                projection_product_version=int(meta["projectionProductVersion"]),
                category=ProductCategory(str(meta["category"])),
                schema_version=int(meta["schemaVersion"]),
                schema_fingerprint=str(meta["schemaFingerprint"]),
                title=DynamoDBCatalogEnrichmentResultRepository._text(records["TITLE"]),
                description=DynamoDBCatalogEnrichmentResultRepository._text(records["DESCRIPTION"]),
                feature_bullets=bullets,
                search_keywords=keywords,
                technical_summary=DynamoDBCatalogEnrichmentResultRepository._text(
                    records["TECHNICAL_SUMMARY"]
                ),
                trusted_fact_count=int(meta["trustedFactCount"]),
                referenced_fact_count=int(meta["referencedFactCount"]),
                fact_coverage_bp=int(meta["factCoverageBp"]),
                grounding_score_bp=int(meta["groundingScoreBp"]),
                warning_codes=tuple(
                    EnrichmentWarningCode(str(value)) for value in meta["warningCodes"]
                ),
                provider=str(meta["provider"]),
                model=str(meta["model"]),
                prompt_version=str(meta["promptVersion"]),
                prompt_sha256=str(meta["promptSha256"]),
                generation_attempt_count=int(meta["generationAttemptCount"]),
                engine=str(meta["engine"]),
                engine_version=str(meta["engineVersion"]),
                created_at=parse_utc(meta["createdAt"]),
            )
        except CatalogEnrichmentResultSerializationError:
            raise
        except (KeyError, TypeError, ValueError, StopIteration) as exc:
            raise CatalogEnrichmentResultSerializationError() from exc

    @staticmethod
    def _ordered(
        records: dict[str, dict[str, Any]], prefix: str, expected: int
    ) -> tuple[GroundedGeneratedText, ...]:
        selected = sorted(
            (item for key, item in records.items() if key.startswith(prefix)),
            key=lambda item: int(item["sequence"]),
        )
        if len(selected) != expected or [int(item["sequence"]) for item in selected] != list(
            range(1, expected + 1)
        ):
            raise CatalogEnrichmentResultSerializationError()
        return tuple(DynamoDBCatalogEnrichmentResultRepository._text(item) for item in selected)

    @staticmethod
    def _text(item: dict[str, Any]) -> GroundedGeneratedText:
        return GroundedGeneratedText(
            text=str(item["text"]), fact_ids=tuple(str(value) for value in item["factIds"])
        )

    def _conditional_put(self, item: dict[str, Any], name: str, field: str) -> dict[str, Any]:
        return {
            "Put": {
                "TableName": self._table_name,
                "Item": serialize_item(item),
                "ConditionExpression": f"attribute_not_exists({name})",
                "ExpressionAttributeNames": {name: field},
            }
        }

    @staticmethod
    def _guard_size(*items: dict[str, Any]) -> None:
        if any(
            len(json.dumps(serialize_item(item), separators=(",", ":"), default=str).encode())
            > MAX_SAFE_ITEM_BYTES
            for item in items
        ):
            raise CatalogEnrichmentResultItemTooLargeError()

    @staticmethod
    def _code(exc: ClientError) -> str:
        return str(exc.response.get("Error", {}).get("Code", ""))
