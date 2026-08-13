"""Immutable DynamoDB repository for category-attribute-schema versions."""

import json
import logging
from collections.abc import Mapping
from typing import cast

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    CategoryAttributeSchemaAlreadyExistsError,
    CategoryAttributeSchemaItemTooLargeError,
    CategoryAttributeSchemaNotAvailableError,
    CategoryAttributeSchemaRepositoryError,
    CategoryAttributeSchemaSerializationError,
    ProductSerializationError,
)
from app.domain.category_schemas import (
    SUPPORTED_SCHEMA_CATEGORIES,
    CategoryAttributeSchema,
    CategoryAttributeSchemaStatus,
)
from app.domain.products import ProductCategory
from app.utils.dynamodb import (
    AttributeValue,
    category_attribute_schema_from_item,
    category_attribute_schema_to_item,
    deserialize_item,
    serialize_item,
)

MAX_SAFE_ITEM_BYTES = 390_000
MAX_ACTIVE_LOOKUP_VERSIONS = 100
logger = logging.getLogger(__name__)


class DynamoDBCategoryAttributeSchemaRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client = client
        self._table_name = table_name

    def create(self, schema: CategoryAttributeSchema) -> CategoryAttributeSchema:
        if schema.status is CategoryAttributeSchemaStatus.ACTIVE:
            active = self.get_active_by_category(schema.category)
            if active is not None and active.version != schema.version:
                raise CategoryAttributeSchemaAlreadyExistsError(
                    "category already has an active schema version"
                )
        try:
            wire_item = serialize_item(category_attribute_schema_to_item(schema))
            size = len(json.dumps(wire_item, separators=(",", ":"), default=str).encode())
            if size > MAX_SAFE_ITEM_BYTES:
                raise CategoryAttributeSchemaItemTooLargeError()
            self._client.put_item(
                TableName=self._table_name,
                Item=wire_item,
                ConditionExpression=(
                    "attribute_not_exists(#category) AND attribute_not_exists(#version)"
                ),
                ExpressionAttributeNames={"#category": "category", "#version": "version"},
            )
        except CategoryAttributeSchemaItemTooLargeError:
            raise
        except ClientError as exc:
            if (
                str(exc.response.get("Error", {}).get("Code", ""))
                == "ConditionalCheckFailedException"
            ):
                raise CategoryAttributeSchemaAlreadyExistsError(
                    "category attribute schema version already exists"
                ) from exc
            raise CategoryAttributeSchemaRepositoryError(
                "category attribute schema could not be created"
            ) from exc
        except (BotoCoreError, ProductSerializationError) as exc:
            raise CategoryAttributeSchemaRepositoryError(
                "category attribute schema could not be created"
            ) from exc
        logger.info(
            "event=category_schema.created category=%s version=%s schema_id=%s "
            "attribute_count=%s required_count=%s fingerprint=%s",
            schema.category.value,
            schema.version,
            schema.schema_id,
            len(schema.attributes),
            sum(attribute.required for attribute in schema.attributes),
            schema.schema_fingerprint,
        )
        return schema

    def get_by_category_and_version(
        self, category: ProductCategory, version: int
    ) -> CategoryAttributeSchema | None:
        _require_supported(category)
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            return None
        try:
            response = self._client.get_item(
                TableName=self._table_name,
                Key=serialize_item({"category": category, "version": version}),
                ConsistentRead=True,
            )
            raw_item = cast(Mapping[str, AttributeValue] | None, response.get("Item"))
            if raw_item is None:
                return None
            schema = category_attribute_schema_from_item(deserialize_item(raw_item))
        except CategoryAttributeSchemaSerializationError:
            raise
        except (BotoCoreError, ClientError) as exc:
            raise CategoryAttributeSchemaRepositoryError(
                "category attribute schema could not be retrieved"
            ) from exc
        logger.info(
            "event=category_schema.retrieved category=%s version=%s schema_id=%s fingerprint=%s",
            category.value,
            version,
            schema.schema_id,
            schema.schema_fingerprint,
        )
        return schema

    def get_active_by_category(self, category: ProductCategory) -> CategoryAttributeSchema | None:
        _require_supported(category)
        try:
            response = self._client.query(
                TableName=self._table_name,
                KeyConditionExpression="#category = :category",
                ExpressionAttributeNames={"#category": "category"},
                ExpressionAttributeValues=serialize_item({":category": category}),
                ScanIndexForward=False,
                Limit=MAX_ACTIVE_LOOKUP_VERSIONS,
                ConsistentRead=True,
            )
            for raw_item in cast(list[Mapping[str, AttributeValue]], response.get("Items", [])):
                schema = category_attribute_schema_from_item(deserialize_item(raw_item))
                if schema.status is CategoryAttributeSchemaStatus.ACTIVE:
                    logger.info(
                        "event=category_schema.active_retrieved category=%s version=%s "
                        "schema_id=%s fingerprint=%s",
                        category.value,
                        schema.version,
                        schema.schema_id,
                        schema.schema_fingerprint,
                    )
                    return schema
            return None
        except CategoryAttributeSchemaSerializationError:
            raise
        except (BotoCoreError, ClientError) as exc:
            raise CategoryAttributeSchemaRepositoryError(
                "active category attribute schema could not be retrieved"
            ) from exc


def _require_supported(category: ProductCategory) -> None:
    if category not in SUPPORTED_SCHEMA_CATEGORIES:
        raise CategoryAttributeSchemaNotAvailableError()
