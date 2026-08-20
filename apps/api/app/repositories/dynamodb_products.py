"""DynamoDB implementation of the product repository contract."""

import hashlib
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    InvalidCatalogSearchCursorError,
    InvalidProductCursorError,
    ProductAlreadyExistsError,
    ProductNotFoundError,
    ProductRepositoryError,
    ProductStatusConflictError,
    ProductVersionConflictError,
)
from app.domain.catalog_search import CatalogSearchAccessPattern, normalize_catalog_search_text
from app.domain.products import Product, ProductCategory, ProductPage, ProductStatus
from app.utils.cursors import (
    decode_catalog_search_cursor,
    decode_product_cursor,
    encode_catalog_search_cursor,
    encode_product_cursor,
)
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
CATEGORY_CREATED_AT_INDEX = "CategoryCreatedAtIndex"
CATEGORY_STATUS_CREATED_AT_INDEX = "CategoryStatusCreatedAtIndex"
MANUFACTURER_CREATED_AT_INDEX = "ManufacturerCreatedAtIndex"
MODEL_NUMBER_CREATED_AT_INDEX = "ModelNumberCreatedAtIndex"
NAME_SEARCH_INDEX = "NameSearchIndex"
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
                ":normalizedName": normalize_catalog_search_text(product.name),
                ":categoryStatusKey": f"{product.category.value}#{product.status.value}",
            }
        )
        set_parts = [
            "#name = :name",
            "#manufacturer = :manufacturer",
            "#modelNumber = :modelNumber",
            "#category = :category",
            "#status = :status",
            "#description = :description",
            "#sourceCount = :sourceCount",
            "#updatedAt = :updatedAt",
            "#version = :newVersion",
            "#normalizedName = :normalizedName",
            "#categoryStatusKey = :categoryStatusKey",
        ]
        remove_parts = []
        if product.manufacturer is None:
            remove_parts.append("#normalizedManufacturer")
        else:
            values.update(
                serialize_item(
                    {":normalizedManufacturer": normalize_catalog_search_text(product.manufacturer)}
                )
            )
            set_parts.append("#normalizedManufacturer = :normalizedManufacturer")
        if product.model_number is None:
            remove_parts.append("#normalizedModelNumber")
        else:
            values.update(
                serialize_item(
                    {":normalizedModelNumber": normalize_catalog_search_text(product.model_number)}
                )
            )
            set_parts.append("#normalizedModelNumber = :normalizedModelNumber")
        update_expression = "SET " + ", ".join(set_parts)
        if remove_parts:
            update_expression += " REMOVE " + ", ".join(remove_parts)
        try:
            response = self._client.update_item(
                TableName=self._table_name,
                Key=serialize_item({"productId": product.product_id}),
                UpdateExpression=update_expression,
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
                    "#normalizedName": "normalizedName",
                    "#normalizedManufacturer": "normalizedManufacturer",
                    "#normalizedModelNumber": "normalizedModelNumber",
                    "#categoryStatusKey": "categoryStatusKey",
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
                self._raise_version_conflict(product.product_id, expected_version, exc)
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

    def mark_ready_to_publish(
        self,
        *,
        product_id: UUID,
        expected_version: int,
        expected_status: ProductStatus,
    ) -> Product:
        """Atomically apply the sole SPEC-032 Product lifecycle transition."""
        _validate_expected_version(expected_version)
        current = self.get_by_id(product_id)
        if current is None:
            raise ProductNotFoundError(product_id)
        updated_at = self._clock().astimezone(UTC)
        try:
            response = self._client.update_item(
                TableName=self._table_name,
                Key=serialize_item({"productId": product_id}),
                UpdateExpression=(
                    "SET #status = :newStatus, #categoryStatusKey = :categoryStatusKey, "
                    "#updatedAt = :updatedAt, #version = :newVersion"
                ),
                ConditionExpression=(
                    "attribute_exists(#productId) AND #version = :expectedVersion "
                    "AND #status = :expectedStatus"
                ),
                ExpressionAttributeNames={
                    "#productId": "productId",
                    "#status": "status",
                    "#updatedAt": "updatedAt",
                    "#version": "version",
                    "#categoryStatusKey": "categoryStatusKey",
                },
                ExpressionAttributeValues=serialize_item(
                    {
                        ":newStatus": ProductStatus.READY_TO_PUBLISH,
                        ":updatedAt": updated_at,
                        ":newVersion": expected_version + 1,
                        ":expectedVersion": expected_version,
                        ":expectedStatus": expected_status,
                        ":categoryStatusKey": (
                            f"{current.category.value}#{ProductStatus.READY_TO_PUBLISH.value}"
                        ),
                    }
                ),
                ReturnValues="ALL_NEW",
            )
            raw_item = response.get("Attributes")
            if raw_item is None:
                raise ProductRepositoryError("transitioned product was not returned")
            return _to_product(cast(Mapping[str, AttributeValue], raw_item))
        except ClientError as exc:
            if _error_code(exc) == "ConditionalCheckFailedException":
                current = self.get_by_id(product_id)
                if current is None:
                    raise ProductNotFoundError(product_id) from exc
                if current.version != expected_version:
                    raise ProductVersionConflictError(
                        f"product {product_id} is not at expected version {expected_version}"
                    ) from exc
                raise ProductStatusConflictError(current.status.value) from exc
            raise ProductRepositoryError("product readiness could not be applied") from exc
        except BotoCoreError as exc:
            raise ProductRepositoryError("product readiness could not be applied") from exc

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

    def list_created(self, *, limit: int = 20, cursor: str | None = None) -> ProductPage:
        return self._query_catalog_products(
            pattern=CatalogSearchAccessPattern.CREATED_AT,
            index_name=CREATED_AT_INDEX,
            key_name="entityType",
            key_value="PRODUCT",
            limit=limit,
            cursor=cursor,
            cursor_keys={"productId", "entityType", "createdAt"},
        )

    def search_by_status(
        self, status: ProductStatus, *, limit: int = 20, cursor: str | None = None
    ) -> ProductPage:
        return self._query_catalog_products(
            pattern=CatalogSearchAccessPattern.STATUS,
            index_name=STATUS_CREATED_AT_INDEX,
            key_name="status",
            key_value=status.value,
            limit=limit,
            cursor=cursor,
            cursor_keys={"productId", "status", "createdAt"},
        )

    def list_by_category(
        self, category: ProductCategory, *, limit: int = 20, cursor: str | None = None
    ) -> ProductPage:
        return self._query_catalog_products(
            pattern=CatalogSearchAccessPattern.CATEGORY,
            index_name=CATEGORY_CREATED_AT_INDEX,
            key_name="category",
            key_value=category.value,
            limit=limit,
            cursor=cursor,
            cursor_keys={"productId", "category", "createdAt"},
        )

    def list_by_category_status(
        self,
        category: ProductCategory,
        status: ProductStatus,
        *,
        limit: int = 20,
        cursor: str | None = None,
    ) -> ProductPage:
        value = f"{category.value}#{status.value}"
        return self._query_catalog_products(
            pattern=CatalogSearchAccessPattern.CATEGORY_STATUS,
            index_name=CATEGORY_STATUS_CREATED_AT_INDEX,
            key_name="categoryStatusKey",
            key_value=value,
            limit=limit,
            cursor=cursor,
            cursor_keys={"productId", "categoryStatusKey", "createdAt"},
        )

    def list_by_manufacturer(
        self, normalized_manufacturer: str, *, limit: int = 20, cursor: str | None = None
    ) -> ProductPage:
        return self._query_catalog_products(
            pattern=CatalogSearchAccessPattern.MANUFACTURER,
            index_name=MANUFACTURER_CREATED_AT_INDEX,
            key_name="normalizedManufacturer",
            key_value=normalize_catalog_search_text(normalized_manufacturer),
            limit=limit,
            cursor=cursor,
            cursor_keys={"productId", "normalizedManufacturer", "createdAt"},
        )

    def list_by_model_number(
        self, normalized_model_number: str, *, limit: int = 20, cursor: str | None = None
    ) -> ProductPage:
        return self._query_catalog_products(
            pattern=CatalogSearchAccessPattern.MODEL_NUMBER,
            index_name=MODEL_NUMBER_CREATED_AT_INDEX,
            key_name="normalizedModelNumber",
            key_value=normalize_catalog_search_text(normalized_model_number),
            limit=limit,
            cursor=cursor,
            cursor_keys={"productId", "normalizedModelNumber", "createdAt"},
        )

    def list_by_name_prefix(
        self, normalized_prefix: str, *, limit: int = 20, cursor: str | None = None
    ) -> ProductPage:
        return self._query_catalog_products(
            pattern=CatalogSearchAccessPattern.NAME_PREFIX,
            index_name=NAME_SEARCH_INDEX,
            key_name="entityType",
            key_value="PRODUCT",
            limit=limit,
            cursor=cursor,
            cursor_keys={"productId", "entityType", "normalizedName"},
            sort_key="normalizedName",
            sort_prefix=normalize_catalog_search_text(normalized_prefix),
            scan_forward=True,
        )

    def delete(self, product_id: UUID, expected_version: int) -> None:
        _validate_expected_version(expected_version)
        try:
            self._client.delete_item(
                TableName=self._table_name,
                Key=serialize_item({"productId": product_id}),
                ConditionExpression=(
                    "attribute_exists(#productId) AND #version = :expectedVersion"
                ),
                ExpressionAttributeNames={"#productId": "productId", "#version": "version"},
                ExpressionAttributeValues=serialize_item({":expectedVersion": expected_version}),
            )
        except ClientError as exc:
            if _error_code(exc) == "ConditionalCheckFailedException":
                self._raise_version_conflict(product_id, expected_version, exc)
            raise ProductRepositoryError("product could not be deleted") from exc
        except BotoCoreError as exc:
            raise ProductRepositoryError("product could not be deleted") from exc

    def _raise_version_conflict(
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

    def _query_catalog_products(
        self,
        *,
        pattern: CatalogSearchAccessPattern,
        index_name: str,
        key_name: str,
        key_value: str,
        limit: int,
        cursor: str | None,
        cursor_keys: set[str],
        sort_key: str | None = None,
        sort_prefix: str | None = None,
        scan_forward: bool = False,
    ) -> ProductPage:
        _validate_limit(limit)
        fingerprint = hashlib.sha256(
            f"{pattern.value}|{key_value}|{sort_prefix or ''}".encode()
        ).hexdigest()
        start_key = decode_catalog_search_cursor(cursor, pattern.value, fingerprint)
        if start_key is not None and set(start_key) != cursor_keys:
            raise InvalidCatalogSearchCursorError()
        names = {"#partition": key_name}
        values: dict[str, object] = {":partition": key_value}
        expression = "#partition = :partition"
        if sort_key is not None and sort_prefix is not None:
            names["#sort"] = sort_key
            values[":prefix"] = sort_prefix
            expression += " AND begins_with(#sort, :prefix)"
        request: dict[str, Any] = {
            "TableName": self._table_name,
            "IndexName": index_name,
            "KeyConditionExpression": expression,
            "ExpressionAttributeNames": names,
            "ExpressionAttributeValues": serialize_item(values),
            "ScanIndexForward": scan_forward,
            "Limit": limit,
        }
        if start_key is not None:
            request["ExclusiveStartKey"] = start_key
        try:
            response = self._client.query(**request)
            raw_items = cast(list[Mapping[str, AttributeValue]], response.get("Items", []))
            items = tuple(_to_product(item) for item in raw_items)
            last_key = cast(WireItem | None, response.get("LastEvaluatedKey"))
            return ProductPage(
                items=items,
                next_cursor=encode_catalog_search_cursor(pattern.value, fingerprint, last_key),
            )
        except ProductRepositoryError:
            raise
        except (BotoCoreError, ClientError) as exc:
            raise ProductRepositoryError("catalog products could not be queried") from exc


def _to_product(item: Mapping[str, AttributeValue]) -> Product:
    return product_from_item(deserialize_item(item))


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))


def _validate_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_PAGE_SIZE:
        raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}")


def _validate_expected_version(expected_version: int) -> None:
    if isinstance(expected_version, bool) or not isinstance(expected_version, int):
        raise ValueError("expected_version must be a positive integer")
    if expected_version < 1:
        raise ValueError("expected_version must be a positive integer")
