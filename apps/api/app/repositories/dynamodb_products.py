"""DynamoDB implementation of the product repository contract."""

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    InvalidProductCursorError,
    ProductAlreadyExistsError,
    ProductNotFoundError,
    ProductRepositoryError,
    ProductVersionConflictError,
)
from app.domain.products import Product, ProductPage, ProductStatus
from app.utils.cursors import decode_product_cursor, encode_product_cursor
from app.utils.dynamodb import (
    AttributeValue,
    WireItem,
    deserialize_item,
    product_from_item,
    product_to_item,
    serialize_item,
)

CREATED_AT_INDEX = "CreatedAtIndex"
STATUS_CREATED_AT_INDEX = "StatusCreatedAtIndex"
MAX_PAGE_SIZE = 100


class DynamoDBProductRepository:
    """Store and query product domain objects through a low-level Boto3 client."""

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

    def create(self, product: Product) -> Product:
        try:
            self._client.put_item(
                TableName=self._table_name,
                Item=serialize_item(product_to_item(product)),
                ConditionExpression="attribute_not_exists(#productId)",
                ExpressionAttributeNames={"#productId": "productId"},
            )
        except ClientError as exc:
            if _error_code(exc) == "ConditionalCheckFailedException":
                raise ProductAlreadyExistsError(product.product_id) from exc
            raise ProductRepositoryError("product could not be created") from exc
        except BotoCoreError as exc:
            raise ProductRepositoryError("product could not be created") from exc
        return product

    def get_by_id(self, product_id: UUID) -> Product | None:
        try:
            response = self._client.get_item(
                TableName=self._table_name,
                Key=serialize_item({"productId": product_id}),
                ConsistentRead=True,
            )
            raw_item = response.get("Item")
            if raw_item is None:
                return None
            return _to_product(cast(Mapping[str, AttributeValue], raw_item))
        except ProductRepositoryError:
            raise
        except (BotoCoreError, ClientError) as exc:
            raise ProductRepositoryError("product could not be retrieved") from exc

    def update(self, product: Product, expected_version: int) -> Product:
        if expected_version < 1:
            raise ValueError("expected_version must be positive")
        updated_at = self._clock().astimezone(UTC)
        values = serialize_item(
            {
                ":name": product.name,
                ":manufacturer": product.manufacturer,
                ":modelNumber": product.model_number,
                ":category": product.category,
                ":status": product.status,
                ":description": product.description,
                ":sourceCount": product.source_count,
                ":updatedAt": updated_at,
                ":newVersion": expected_version + 1,
                ":expectedVersion": expected_version,
            }
        )
        try:
            response = self._client.update_item(
                TableName=self._table_name,
                Key=serialize_item({"productId": product.product_id}),
                UpdateExpression=(
                    "SET #name = :name, #manufacturer = :manufacturer, "
                    "#modelNumber = :modelNumber, #category = :category, #status = :status, "
                    "#description = :description, #sourceCount = :sourceCount, "
                    "#updatedAt = :updatedAt, #version = :newVersion"
                ),
                ConditionExpression="attribute_exists(#productId) AND #version = :expectedVersion",
                ExpressionAttributeNames={
                    "#productId": "productId",
                    "#name": "name",
                    "#manufacturer": "manufacturer",
                    "#modelNumber": "modelNumber",
                    "#category": "category",
                    "#status": "status",
                    "#description": "description",
                    "#sourceCount": "sourceCount",
                    "#updatedAt": "updatedAt",
                    "#version": "version",
                },
                ExpressionAttributeValues=values,
                ReturnValues="ALL_NEW",
            )
            raw_item = response.get("Attributes")
            if raw_item is None:
                raise ProductRepositoryError("updated product was not returned")
            return _to_product(cast(Mapping[str, AttributeValue], raw_item))
        except ClientError as exc:
            if _error_code(exc) == "ConditionalCheckFailedException":
                self._raise_update_conflict(product.product_id, expected_version, exc)
            raise ProductRepositoryError("product could not be updated") from exc
        except BotoCoreError as exc:
            raise ProductRepositoryError("product could not be updated") from exc

    def list_products(self, *, limit: int = 25, cursor: str | None = None) -> ProductPage:
        return self._query_products(
            index_name=CREATED_AT_INDEX,
            key_name="entityType",
            key_value="PRODUCT",
            limit=limit,
            cursor=cursor,
            cursor_keys={"productId", "entityType", "createdAt"},
        )

    def list_by_status(
        self,
        status: ProductStatus,
        *,
        limit: int = 25,
        cursor: str | None = None,
    ) -> ProductPage:
        return self._query_products(
            index_name=STATUS_CREATED_AT_INDEX,
            key_name="status",
            key_value=status.value,
            limit=limit,
            cursor=cursor,
            cursor_keys={"productId", "status", "createdAt"},
        )

    def delete(self, product_id: UUID) -> None:
        try:
            self._client.delete_item(
                TableName=self._table_name,
                Key=serialize_item({"productId": product_id}),
                ConditionExpression="attribute_exists(#productId)",
                ExpressionAttributeNames={"#productId": "productId"},
            )
        except ClientError as exc:
            if _error_code(exc) == "ConditionalCheckFailedException":
                raise ProductNotFoundError(product_id) from exc
            raise ProductRepositoryError("product could not be deleted") from exc
        except BotoCoreError as exc:
            raise ProductRepositoryError("product could not be deleted") from exc

    def _raise_update_conflict(
        self, product_id: UUID, expected_version: int, original: ClientError
    ) -> None:
        current = self.get_by_id(product_id)
        if current is None:
            raise ProductNotFoundError(product_id) from original
        raise ProductVersionConflictError(
            f"product {product_id} is not at expected version {expected_version}"
        ) from original

    def _query_products(
        self,
        *,
        index_name: str,
        key_name: str,
        key_value: str,
        limit: int,
        cursor: str | None,
        cursor_keys: set[str],
    ) -> ProductPage:
        _validate_limit(limit)
        start_key = decode_product_cursor(cursor)
        if start_key is not None and set(start_key) != cursor_keys:
            raise InvalidProductCursorError("product cursor does not match this listing")
        request: dict[str, Any] = {
            "TableName": self._table_name,
            "IndexName": index_name,
            "KeyConditionExpression": "#partition = :partition",
            "ExpressionAttributeNames": {"#partition": key_name},
            "ExpressionAttributeValues": serialize_item({":partition": key_value}),
            "ScanIndexForward": False,
            "Limit": limit,
        }
        if start_key is not None:
            request["ExclusiveStartKey"] = start_key
        try:
            response = self._client.query(**request)
            raw_items = cast(list[Mapping[str, AttributeValue]], response.get("Items", []))
            items = tuple(_to_product(item) for item in raw_items)
            last_key = cast(WireItem | None, response.get("LastEvaluatedKey"))
            return ProductPage(items=items, next_cursor=encode_product_cursor(last_key))
        except ProductRepositoryError:
            raise
        except (BotoCoreError, ClientError) as exc:
            raise ProductRepositoryError("products could not be listed") from exc


def _to_product(item: Mapping[str, AttributeValue]) -> Product:
    return product_from_item(deserialize_item(item))


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))


def _validate_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_PAGE_SIZE:
        raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}")
