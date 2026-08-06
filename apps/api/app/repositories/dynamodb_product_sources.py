"""DynamoDB implementation of the product-source repository contract."""

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    InvalidProductSourceCursorError,
    ProductSerializationError,
    ProductSourceAlreadyExistsError,
    ProductSourceNotFoundError,
    ProductSourceRepositoryError,
    ProductSourceSerializationError,
    ProductSourceVersionConflictError,
)
from app.domain.product_sources import ProductSource, ProductSourcePage
from app.utils.cursors import decode_product_source_cursor, encode_product_source_cursor
from app.utils.dynamodb import (
    AttributeValue,
    WireItem,
    deserialize_item,
    product_source_from_item,
    product_source_to_item,
    serialize_item,
)

PRODUCT_CREATED_AT_INDEX = "ProductCreatedAtIndex"
MAX_SOURCE_PAGE_SIZE = 100


class DynamoDBProductSourceRepository:
    """Store and query source metadata through a low-level Boto3 client."""

    def __init__(
        self,
        client: BaseClient,
        table_name: str,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client
        self._table_name = table_name
        self._clock = clock or (lambda: datetime.now(UTC))

    def create(self, source: ProductSource) -> ProductSource:
        try:
            self._client.put_item(
                TableName=self._table_name,
                Item=serialize_item(product_source_to_item(source)),
                ConditionExpression=(
                    "attribute_not_exists(#productId) AND attribute_not_exists(#sourceId)"
                ),
                ExpressionAttributeNames={
                    "#productId": "productId",
                    "#sourceId": "sourceId",
                },
            )
        except ClientError as exc:
            if _error_code(exc) == "ConditionalCheckFailedException":
                raise ProductSourceAlreadyExistsError("product source already exists") from exc
            raise ProductSourceRepositoryError("product source could not be created") from exc
        except BotoCoreError as exc:
            raise ProductSourceRepositoryError("product source could not be created") from exc
        return source

    def get_by_id(self, product_id: UUID, source_id: UUID) -> ProductSource | None:
        try:
            response = self._client.get_item(
                TableName=self._table_name,
                Key=_source_key(product_id, source_id),
                ConsistentRead=True,
            )
            raw_item = response.get("Item")
            if raw_item is None:
                return None
            return _to_source(cast(Mapping[str, AttributeValue], raw_item))
        except ProductSourceRepositoryError:
            raise
        except (BotoCoreError, ClientError) as exc:
            raise ProductSourceRepositoryError("product source could not be retrieved") from exc

    def update(self, source: ProductSource, expected_version: int) -> ProductSource:
        _validate_expected_version(expected_version)
        values = serialize_item(
            {
                ":status": source.status,
                ":storageKey": source.storage_key,
                ":mimeType": source.mime_type,
                ":fileSizeBytes": source.file_size_bytes,
                ":checksumSha256": source.checksum_sha256,
                ":displayName": source.display_name,
                ":textContent": source.text_content,
                ":errorMessage": source.error_message,
                ":updatedAt": self._clock().astimezone(UTC),
                ":newVersion": expected_version + 1,
                ":expectedVersion": expected_version,
            }
        )
        try:
            response = self._client.update_item(
                TableName=self._table_name,
                Key=_source_key(source.product_id, source.source_id),
                UpdateExpression=(
                    "SET #status = :status, #storageKey = :storageKey, #mimeType = :mimeType, "
                    "#fileSizeBytes = :fileSizeBytes, #checksumSha256 = :checksumSha256, "
                    "#displayName = :displayName, #textContent = :textContent, "
                    "#errorMessage = :errorMessage, #updatedAt = :updatedAt, "
                    "#version = :newVersion"
                ),
                ConditionExpression=(
                    "attribute_exists(#productId) AND attribute_exists(#sourceId) "
                    "AND #version = :expectedVersion"
                ),
                ExpressionAttributeNames={
                    "#productId": "productId",
                    "#sourceId": "sourceId",
                    "#status": "status",
                    "#storageKey": "storageKey",
                    "#mimeType": "mimeType",
                    "#fileSizeBytes": "fileSizeBytes",
                    "#checksumSha256": "checksumSha256",
                    "#displayName": "displayName",
                    "#textContent": "textContent",
                    "#errorMessage": "errorMessage",
                    "#updatedAt": "updatedAt",
                    "#version": "version",
                },
                ExpressionAttributeValues=values,
                ReturnValues="ALL_NEW",
            )
            raw_item = response.get("Attributes")
            if raw_item is None:
                raise ProductSourceRepositoryError("updated product source was not returned")
            return _to_source(cast(Mapping[str, AttributeValue], raw_item))
        except ClientError as exc:
            if _error_code(exc) == "ConditionalCheckFailedException":
                self._raise_mutation_conflict(
                    source.product_id, source.source_id, expected_version, exc
                )
            raise ProductSourceRepositoryError("product source could not be updated") from exc
        except BotoCoreError as exc:
            raise ProductSourceRepositoryError("product source could not be updated") from exc

    def list_by_product(
        self,
        product_id: UUID,
        *,
        limit: int = 25,
        cursor: str | None = None,
    ) -> ProductSourcePage:
        _validate_limit(limit)
        start_key = decode_product_source_cursor(cursor, product_id)
        if start_key is not None and set(start_key) != {"productId", "sourceId", "createdAt"}:
            raise InvalidProductSourceCursorError(
                "product-source cursor does not match source listing"
            )
        request: dict[str, Any] = {
            "TableName": self._table_name,
            "IndexName": PRODUCT_CREATED_AT_INDEX,
            "KeyConditionExpression": "#productId = :productId",
            "ExpressionAttributeNames": {"#productId": "productId"},
            "ExpressionAttributeValues": serialize_item({":productId": product_id}),
            "ScanIndexForward": False,
            "Limit": limit,
        }
        if start_key is not None:
            request["ExclusiveStartKey"] = start_key
        try:
            response = self._client.query(**request)
            raw_items = cast(list[Mapping[str, AttributeValue]], response.get("Items", []))
            items = tuple(_to_source(item) for item in raw_items)
            last_key = cast(WireItem | None, response.get("LastEvaluatedKey"))
            return ProductSourcePage(
                items=items,
                next_cursor=encode_product_source_cursor(product_id, last_key),
            )
        except ProductSourceRepositoryError:
            raise
        except (BotoCoreError, ClientError) as exc:
            raise ProductSourceRepositoryError("product sources could not be listed") from exc

    def delete(self, product_id: UUID, source_id: UUID, expected_version: int) -> None:
        _validate_expected_version(expected_version)
        try:
            self._client.delete_item(
                TableName=self._table_name,
                Key=_source_key(product_id, source_id),
                ConditionExpression=(
                    "attribute_exists(#productId) AND attribute_exists(#sourceId) "
                    "AND #version = :expectedVersion"
                ),
                ExpressionAttributeNames={
                    "#productId": "productId",
                    "#sourceId": "sourceId",
                    "#version": "version",
                },
                ExpressionAttributeValues=serialize_item({":expectedVersion": expected_version}),
            )
        except ClientError as exc:
            if _error_code(exc) == "ConditionalCheckFailedException":
                self._raise_mutation_conflict(product_id, source_id, expected_version, exc)
            raise ProductSourceRepositoryError("product source could not be deleted") from exc
        except BotoCoreError as exc:
            raise ProductSourceRepositoryError("product source could not be deleted") from exc

    def _raise_mutation_conflict(
        self,
        product_id: UUID,
        source_id: UUID,
        expected_version: int,
        original: ClientError,
    ) -> None:
        current = self.get_by_id(product_id, source_id)
        if current is None:
            raise ProductSourceNotFoundError("product source does not exist") from original
        raise ProductSourceVersionConflictError(
            f"product source is not at expected version {expected_version}"
        ) from original


def _source_key(product_id: UUID, source_id: UUID) -> WireItem:
    return serialize_item({"productId": product_id, "sourceId": source_id})


def _to_source(item: Mapping[str, AttributeValue]) -> ProductSource:
    try:
        return product_source_from_item(deserialize_item(item))
    except ProductSourceSerializationError:
        raise
    except ProductSerializationError as exc:
        raise ProductSourceSerializationError(
            "DynamoDB item is not a valid product source"
        ) from exc


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))


def _validate_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError(f"limit must be between 1 and {MAX_SOURCE_PAGE_SIZE}")


def _validate_expected_version(expected_version: int) -> None:
    if isinstance(expected_version, bool) or not isinstance(expected_version, int):
        raise ValueError("expected_version must be a positive integer")
    if expected_version < 1:
        raise ValueError("expected_version must be a positive integer")
