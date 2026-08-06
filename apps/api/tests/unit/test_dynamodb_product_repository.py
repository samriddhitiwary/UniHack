"""DynamoDB product repository tests using Botocore's approved request stubber."""

from dataclasses import replace

import boto3
import pytest
from botocore.client import BaseClient
from botocore.stub import Stubber

from app.core.exceptions import (
    InvalidProductCursorError,
    ProductAlreadyExistsError,
    ProductNotFoundError,
    ProductRepositoryError,
    ProductVersionConflictError,
)
from app.domain.products import Product, ProductStatus
from app.repositories.dynamodb_products import (
    CREATED_AT_INDEX,
    STATUS_CREATED_AT_INDEX,
    DynamoDBProductRepository,
)
from app.utils.dynamodb import product_to_item, serialize_item
from tests.fixtures.products import (
    PRODUCT_ID,
    SECOND_PRODUCT_ID,
    UPDATED_AT,
    make_product,
)

TABLE_NAME = "catalogiq-test-products"


@pytest.fixture
def dynamodb_client() -> BaseClient:
    return boto3.client(
        "dynamodb",
        region_name="ap-south-1",
        endpoint_url="http://localhost:8001",
        aws_access_key_id="local",
        aws_secret_access_key="local",
    )


def test_create_product_uses_conditional_write(dynamodb_client: BaseClient) -> None:
    product = make_product()
    expected = _create_request(product)
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response("put_item", {}, expected)
        repository = DynamoDBProductRepository(dynamodb_client, TABLE_NAME)
        assert repository.create(product) == product


def test_duplicate_product_raises_conflict(dynamodb_client: BaseClient) -> None:
    product = make_product()
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "put_item",
            service_error_code="ConditionalCheckFailedException",
            expected_params=_create_request(product),
        )
        repository = DynamoDBProductRepository(dynamodb_client, TABLE_NAME)
        with pytest.raises(ProductAlreadyExistsError) as captured:
            repository.create(product)
        assert captured.value.__cause__ is not None


def test_retrieve_product_and_missing_product(dynamodb_client: BaseClient) -> None:
    product = make_product()
    expected = _get_request()
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response(
            "get_item", {"Item": serialize_item(product_to_item(product))}, expected
        )
        stubber.add_response("get_item", {}, expected)
        repository = DynamoDBProductRepository(dynamodb_client, TABLE_NAME)
        assert repository.get_by_id(PRODUCT_ID) == product
        assert repository.get_by_id(PRODUCT_ID) is None


def test_update_uses_expected_version_and_returns_incremented_record(
    dynamodb_client: BaseClient,
) -> None:
    product = make_product()
    expected_product = replace(product, updated_at=UPDATED_AT, version=2)
    expected_request = _update_request(product, expected_version=1)
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response(
            "update_item",
            {"Attributes": serialize_item(product_to_item(expected_product))},
            expected_request,
        )
        repository = DynamoDBProductRepository(
            dynamodb_client, TABLE_NAME, clock=lambda: UPDATED_AT
        )
        updated = repository.update(product, expected_version=1)
    assert updated == expected_product


def test_stale_update_raises_version_conflict(dynamodb_client: BaseClient) -> None:
    product = make_product()
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "update_item",
            service_error_code="ConditionalCheckFailedException",
            expected_params=_update_request(product, expected_version=1),
        )
        stubber.add_response(
            "get_item", {"Item": serialize_item(product_to_item(product))}, _get_request()
        )
        repository = DynamoDBProductRepository(
            dynamodb_client, TABLE_NAME, clock=lambda: UPDATED_AT
        )
        with pytest.raises(ProductVersionConflictError):
            repository.update(product, expected_version=1)


def test_update_missing_product_raises_not_found(dynamodb_client: BaseClient) -> None:
    product = make_product()
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "update_item",
            service_error_code="ConditionalCheckFailedException",
            expected_params=_update_request(product, expected_version=1),
        )
        stubber.add_response("get_item", {}, _get_request())
        repository = DynamoDBProductRepository(
            dynamodb_client, TABLE_NAME, clock=lambda: UPDATED_AT
        )
        with pytest.raises(ProductNotFoundError):
            repository.update(product, expected_version=1)


def test_list_products_paginates_across_created_at_index(
    dynamodb_client: BaseClient,
) -> None:
    first = make_product()
    second = make_product(product_id=SECOND_PRODUCT_ID, name="IM-20 Induction Motor")
    last_key = serialize_item(
        {
            "productId": first.product_id,
            "entityType": "PRODUCT",
            "createdAt": first.created_at,
        }
    )
    first_request = _query_request(
        index_name=CREATED_AT_INDEX,
        key_name="entityType",
        key_value="PRODUCT",
        limit=1,
    )
    second_request = {**first_request, "ExclusiveStartKey": last_key}
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response(
            "query",
            {
                "Items": [serialize_item(product_to_item(first))],
                "LastEvaluatedKey": last_key,
            },
            first_request,
        )
        stubber.add_response(
            "query", {"Items": [serialize_item(product_to_item(second))]}, second_request
        )
        repository = DynamoDBProductRepository(dynamodb_client, TABLE_NAME)
        first_page = repository.list_products(limit=1)
        assert first_page.items == (first,)
        assert first_page.next_cursor is not None
        second_page = repository.list_products(limit=1, cursor=first_page.next_cursor)
        assert second_page.items == (second,)
        assert second_page.next_cursor is None


def test_list_by_status_uses_status_index(dynamodb_client: BaseClient) -> None:
    product = make_product(status=ProductStatus.REVIEW_REQUIRED)
    expected = _query_request(
        index_name=STATUS_CREATED_AT_INDEX,
        key_name="status",
        key_value=ProductStatus.REVIEW_REQUIRED.value,
        limit=25,
    )
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response(
            "query", {"Items": [serialize_item(product_to_item(product))]}, expected
        )
        repository = DynamoDBProductRepository(dynamodb_client, TABLE_NAME)
        page = repository.list_by_status(ProductStatus.REVIEW_REQUIRED)
    assert page.items == (product,)


def test_listing_rejects_invalid_limit_and_wrong_cursor(dynamodb_client: BaseClient) -> None:
    repository = DynamoDBProductRepository(dynamodb_client, TABLE_NAME)
    with pytest.raises(ValueError, match="limit"):
        repository.list_products(limit=0)
    wrong_cursor = "eyJzdGF0dXMiOnsiUyI6IkRSQUZUIn19"
    with pytest.raises(InvalidProductCursorError):
        repository.list_products(cursor=wrong_cursor)


def test_delete_product_uses_expected_version(dynamodb_client: BaseClient) -> None:
    expected = _delete_request(expected_version=2)
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response("delete_item", {}, expected)
        repository = DynamoDBProductRepository(dynamodb_client, TABLE_NAME)
        repository.delete(PRODUCT_ID, expected_version=2)


def test_stale_delete_raises_version_conflict(dynamodb_client: BaseClient) -> None:
    product = make_product(version=2)
    expected = _delete_request(expected_version=1)
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "delete_item",
            service_error_code="ConditionalCheckFailedException",
            expected_params=expected,
        )
        stubber.add_response(
            "get_item", {"Item": serialize_item(product_to_item(product))}, _get_request()
        )
        repository = DynamoDBProductRepository(dynamodb_client, TABLE_NAME)
        with pytest.raises(ProductVersionConflictError):
            repository.delete(PRODUCT_ID, expected_version=1)


def test_missing_delete_raises_not_found(dynamodb_client: BaseClient) -> None:
    expected = _delete_request(expected_version=1)
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "delete_item",
            service_error_code="ConditionalCheckFailedException",
            expected_params=expected,
        )
        stubber.add_response("get_item", {}, _get_request())
        repository = DynamoDBProductRepository(dynamodb_client, TABLE_NAME)
        with pytest.raises(ProductNotFoundError):
            repository.delete(PRODUCT_ID, expected_version=1)


@pytest.mark.parametrize("expected_version", [0, -1, True, 1.5])
def test_delete_rejects_invalid_expected_version(
    dynamodb_client: BaseClient, expected_version: object
) -> None:
    repository = DynamoDBProductRepository(dynamodb_client, TABLE_NAME)
    with pytest.raises(ValueError):
        repository.delete(PRODUCT_ID, expected_version)  # type: ignore[arg-type]


def test_delete_boto_failure_is_wrapped(dynamodb_client: BaseClient) -> None:
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "delete_item",
            service_error_code="InternalServerError",
            expected_params=_delete_request(expected_version=1),
        )
        repository = DynamoDBProductRepository(dynamodb_client, TABLE_NAME)
        with pytest.raises(ProductRepositoryError) as captured:
            repository.delete(PRODUCT_ID, expected_version=1)
        assert captured.value.__cause__ is not None


def test_boto_failure_is_wrapped(dynamodb_client: BaseClient) -> None:
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "get_item",
            service_error_code="InternalServerError",
            expected_params=_get_request(),
        )
        repository = DynamoDBProductRepository(dynamodb_client, TABLE_NAME)
        with pytest.raises(ProductRepositoryError) as captured:
            repository.get_by_id(PRODUCT_ID)
        assert captured.value.__cause__ is not None


def _create_request(product: Product) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "Item": serialize_item(product_to_item(product)),
        "ConditionExpression": "attribute_not_exists(#productId)",
        "ExpressionAttributeNames": {"#productId": "productId"},
    }


def _get_request() -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "Key": serialize_item({"productId": PRODUCT_ID}),
        "ConsistentRead": True,
    }


def _update_request(product: Product, expected_version: int) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "Key": serialize_item({"productId": product.product_id}),
        "UpdateExpression": (
            "SET #name = :name, #manufacturer = :manufacturer, "
            "#modelNumber = :modelNumber, #category = :category, #status = :status, "
            "#description = :description, #sourceCount = :sourceCount, "
            "#updatedAt = :updatedAt, #version = :newVersion"
        ),
        "ConditionExpression": "attribute_exists(#productId) AND #version = :expectedVersion",
        "ExpressionAttributeNames": {
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
        "ExpressionAttributeValues": serialize_item(
            {
                ":name": product.name,
                ":manufacturer": product.manufacturer,
                ":modelNumber": product.model_number,
                ":category": product.category,
                ":status": product.status,
                ":description": product.description,
                ":sourceCount": product.source_count,
                ":updatedAt": UPDATED_AT,
                ":newVersion": expected_version + 1,
                ":expectedVersion": expected_version,
            }
        ),
        "ReturnValues": "ALL_NEW",
    }


def _delete_request(expected_version: int) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "Key": serialize_item({"productId": PRODUCT_ID}),
        "ConditionExpression": "attribute_exists(#productId) AND #version = :expectedVersion",
        "ExpressionAttributeNames": {"#productId": "productId", "#version": "version"},
        "ExpressionAttributeValues": serialize_item({":expectedVersion": expected_version}),
    }


def _query_request(
    *, index_name: str, key_name: str, key_value: str, limit: int
) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "IndexName": index_name,
        "KeyConditionExpression": "#partition = :partition",
        "ExpressionAttributeNames": {"#partition": key_name},
        "ExpressionAttributeValues": serialize_item({":partition": key_value}),
        "ScanIndexForward": False,
        "Limit": limit,
    }
