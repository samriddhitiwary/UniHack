"""Atomic Product publishing-readiness transition repository tests."""

from dataclasses import replace

import boto3
import pytest
from botocore.client import BaseClient
from botocore.stub import Stubber

from app.core.exceptions import (
    ProductNotFoundError,
    ProductRepositoryError,
    ProductStatusConflictError,
    ProductVersionConflictError,
)
from app.domain.products import Product, ProductStatus
from app.repositories.dynamodb_products import DynamoDBProductRepository
from app.utils.dynamodb import product_to_item, serialize_item
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.catalog_projection import projected_result

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


def test_transition_conditionally_changes_only_status_version_and_updated_at(
    dynamodb_client: BaseClient,
) -> None:
    product, _, _ = projected_result()
    expected = replace(
        product,
        status=ProductStatus.READY_TO_PUBLISH,
        version=4,
        updated_at=NOW,
    )
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response(
            "update_item",
            {"Attributes": serialize_item(product_to_item(expected))},
            _transition_request(product),
        )
        repository = DynamoDBProductRepository(dynamodb_client, TABLE_NAME, clock=lambda: NOW)
        result = repository.mark_ready_to_publish(
            product_id=product.product_id,
            expected_version=3,
            expected_status=ProductStatus.REVIEW_REQUIRED,
        )
    assert result == expected
    assert result.name == product.name
    assert result.manufacturer == product.manufacturer
    assert result.model_number == product.model_number
    assert result.category == product.category
    assert result.description == product.description


@pytest.mark.parametrize(
    ("current", "error"),
    [
        (lambda product: replace(product, version=4), ProductVersionConflictError),
        (lambda product: replace(product, status=ProductStatus.FAILED), ProductStatusConflictError),
    ],
)
def test_conditional_failure_is_classified_with_safe_follow_up_read(
    dynamodb_client: BaseClient, current, error: type[Exception]
) -> None:
    product, _, _ = projected_result()
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "update_item",
            service_error_code="ConditionalCheckFailedException",
            expected_params=_transition_request(product),
        )
        stubber.add_response(
            "get_item",
            {"Item": serialize_item(product_to_item(current(product)))},
            _get_request(product),
        )
        repository = DynamoDBProductRepository(dynamodb_client, TABLE_NAME, clock=lambda: NOW)
        with pytest.raises(error):
            repository.mark_ready_to_publish(
                product_id=product.product_id,
                expected_version=3,
                expected_status=ProductStatus.REVIEW_REQUIRED,
            )


def test_conditional_failure_for_missing_product_is_not_found(
    dynamodb_client: BaseClient,
) -> None:
    product, _, _ = projected_result()
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "update_item",
            service_error_code="ConditionalCheckFailedException",
            expected_params=_transition_request(product),
        )
        stubber.add_response("get_item", {}, _get_request(product))
        repository = DynamoDBProductRepository(dynamodb_client, TABLE_NAME, clock=lambda: NOW)
        with pytest.raises(ProductNotFoundError):
            repository.mark_ready_to_publish(
                product_id=product.product_id,
                expected_version=3,
                expected_status=ProductStatus.REVIEW_REQUIRED,
            )


def test_transition_wraps_storage_failure(dynamodb_client: BaseClient) -> None:
    product, _, _ = projected_result()
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "update_item",
            service_error_code="InternalServerError",
            expected_params=_transition_request(product),
        )
        repository = DynamoDBProductRepository(dynamodb_client, TABLE_NAME, clock=lambda: NOW)
        with pytest.raises(ProductRepositoryError):
            repository.mark_ready_to_publish(
                product_id=product.product_id,
                expected_version=3,
                expected_status=ProductStatus.REVIEW_REQUIRED,
            )


@pytest.mark.parametrize("version", [0, -1, True, 1.5])
def test_transition_rejects_invalid_expected_version(
    dynamodb_client: BaseClient, version: object
) -> None:
    product, _, _ = projected_result()
    repository = DynamoDBProductRepository(dynamodb_client, TABLE_NAME)
    with pytest.raises(ValueError):
        repository.mark_ready_to_publish(
            product_id=product.product_id,
            expected_version=version,  # type: ignore[arg-type]
            expected_status=ProductStatus.REVIEW_REQUIRED,
        )


def _transition_request(product: Product) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "Key": serialize_item({"productId": product.product_id}),
        "UpdateExpression": (
            "SET #status = :newStatus, #updatedAt = :updatedAt, #version = :newVersion"
        ),
        "ConditionExpression": (
            "attribute_exists(#productId) AND #version = :expectedVersion "
            "AND #status = :expectedStatus"
        ),
        "ExpressionAttributeNames": {
            "#productId": "productId",
            "#status": "status",
            "#updatedAt": "updatedAt",
            "#version": "version",
        },
        "ExpressionAttributeValues": serialize_item(
            {
                ":newStatus": ProductStatus.READY_TO_PUBLISH,
                ":updatedAt": NOW,
                ":newVersion": 4,
                ":expectedVersion": 3,
                ":expectedStatus": ProductStatus.REVIEW_REQUIRED,
            }
        ),
        "ReturnValues": "ALL_NEW",
    }


def _get_request(product: Product) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "Key": serialize_item({"productId": product.product_id}),
        "ConsistentRead": True,
    }
