"""DynamoDB product-source repository request-contract tests."""

from dataclasses import replace
from uuid import uuid4

import boto3
import pytest
from botocore.client import BaseClient
from botocore.stub import Stubber

from app.core.exceptions import (
    InvalidProductSourceCursorError,
    ProductSourceAlreadyExistsError,
    ProductSourceNotFoundError,
    ProductSourceRepositoryError,
    ProductSourceVersionConflictError,
)
from app.domain.product_sources import ProductSource, ProductSourceStatus
from app.repositories.dynamodb_product_sources import (
    PRODUCT_CREATED_AT_INDEX,
    DynamoDBProductSourceRepository,
)
from app.utils.cursors import encode_product_source_cursor
from app.utils.dynamodb import product_source_to_item, serialize_item
from tests.fixtures.product_sources import (
    SECOND_SOURCE_ID,
    SOURCE_CREATED_AT,
    SOURCE_ID,
    SOURCE_UPDATED_AT,
    make_product_source,
)
from tests.fixtures.products import PRODUCT_ID

TABLE_NAME = "catalogiq-test-sources"


@pytest.fixture
def dynamodb_client() -> BaseClient:
    return boto3.client(
        "dynamodb",
        region_name="ap-south-1",
        endpoint_url="http://localhost:8001",
        aws_access_key_id="local",
        aws_secret_access_key="local",
    )


def test_create_source_uses_conditional_composite_key(dynamodb_client: BaseClient) -> None:
    source = make_product_source()
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response("put_item", {}, _create_request(source))
        repository = DynamoDBProductSourceRepository(dynamodb_client, TABLE_NAME)
        assert repository.create(source) == source


def test_duplicate_source_raises_controlled_error(dynamodb_client: BaseClient) -> None:
    source = make_product_source()
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "put_item",
            service_error_code="ConditionalCheckFailedException",
            expected_params=_create_request(source),
        )
        repository = DynamoDBProductSourceRepository(dynamodb_client, TABLE_NAME)
        with pytest.raises(ProductSourceAlreadyExistsError):
            repository.create(source)


def test_get_source_and_missing_source(dynamodb_client: BaseClient) -> None:
    source = make_product_source()
    expected = _get_request(PRODUCT_ID, SOURCE_ID)
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response(
            "get_item", {"Item": serialize_item(product_source_to_item(source))}, expected
        )
        stubber.add_response("get_item", {}, expected)
        repository = DynamoDBProductSourceRepository(dynamodb_client, TABLE_NAME)
        assert repository.get_by_id(PRODUCT_ID, SOURCE_ID) == source
        assert repository.get_by_id(PRODUCT_ID, SOURCE_ID) is None


def test_list_sources_uses_gsi_newest_first_and_paginates(
    dynamodb_client: BaseClient,
) -> None:
    first = make_product_source()
    second = make_product_source(source_id=SECOND_SOURCE_ID, display_name="Second")
    last_key = serialize_item(
        {"productId": PRODUCT_ID, "sourceId": SOURCE_ID, "createdAt": SOURCE_CREATED_AT}
    )
    first_request = _query_request(limit=1)
    second_request = {**first_request, "ExclusiveStartKey": last_key}
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response(
            "query",
            {
                "Items": [serialize_item(product_source_to_item(first))],
                "LastEvaluatedKey": last_key,
            },
            first_request,
        )
        stubber.add_response(
            "query",
            {"Items": [serialize_item(product_source_to_item(second))]},
            second_request,
        )
        repository = DynamoDBProductSourceRepository(dynamodb_client, TABLE_NAME)
        first_page = repository.list_by_product(PRODUCT_ID, limit=1)
        assert first_page.items == (first,)
        assert first_page.next_cursor is not None
        second_page = repository.list_by_product(PRODUCT_ID, limit=1, cursor=first_page.next_cursor)
        assert second_page.items == (second,)
        assert second_page.next_cursor is None


def test_listing_rejects_limit_malformed_cursor_and_other_product(
    dynamodb_client: BaseClient,
) -> None:
    repository = DynamoDBProductSourceRepository(dynamodb_client, TABLE_NAME)
    with pytest.raises(ValueError):
        repository.list_by_product(PRODUCT_ID, limit=0)
    with pytest.raises(InvalidProductSourceCursorError):
        repository.list_by_product(PRODUCT_ID, cursor="malformed")
    key = serialize_item(
        {"productId": PRODUCT_ID, "sourceId": SOURCE_ID, "createdAt": SOURCE_CREATED_AT}
    )
    other_cursor = encode_product_source_cursor(uuid4(), key)
    with pytest.raises(InvalidProductSourceCursorError):
        repository.list_by_product(PRODUCT_ID, cursor=other_cursor)


def test_update_metadata_status_version_and_timestamp(dynamodb_client: BaseClient) -> None:
    source = replace(
        make_product_source(),
        status=ProductSourceStatus.COMPLETED,
        display_name="Completed source",
    )
    expected_source = replace(source, updated_at=SOURCE_UPDATED_AT, version=2)
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response(
            "update_item",
            {"Attributes": serialize_item(product_source_to_item(expected_source))},
            _update_request(source, expected_version=1),
        )
        repository = DynamoDBProductSourceRepository(
            dynamodb_client, TABLE_NAME, clock=lambda: SOURCE_UPDATED_AT
        )
        updated = repository.update(source, expected_version=1)
    assert updated == expected_source
    assert updated.source_id == source.source_id
    assert updated.product_id == source.product_id
    assert updated.source_type == source.source_type
    assert updated.created_at == source.created_at


@pytest.mark.parametrize("missing", [False, True])
def test_update_conditional_failure_distinguishes_conflict_and_missing(
    dynamodb_client: BaseClient, missing: bool
) -> None:
    source = make_product_source()
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "update_item",
            service_error_code="ConditionalCheckFailedException",
            expected_params=_update_request(source, expected_version=1),
        )
        response = {} if missing else {"Item": serialize_item(product_source_to_item(source))}
        stubber.add_response("get_item", response, _get_request(PRODUCT_ID, SOURCE_ID))
        repository = DynamoDBProductSourceRepository(
            dynamodb_client, TABLE_NAME, clock=lambda: SOURCE_UPDATED_AT
        )
        expected_error = (
            ProductSourceNotFoundError if missing else ProductSourceVersionConflictError
        )
        with pytest.raises(expected_error):
            repository.update(source, expected_version=1)


def test_delete_uses_composite_key_and_expected_version(dynamodb_client: BaseClient) -> None:
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response("delete_item", {}, _delete_request(expected_version=2))
        repository = DynamoDBProductSourceRepository(dynamodb_client, TABLE_NAME)
        repository.delete(PRODUCT_ID, SOURCE_ID, expected_version=2)


@pytest.mark.parametrize("missing", [False, True])
def test_delete_conditional_failure_distinguishes_conflict_and_missing(
    dynamodb_client: BaseClient, missing: bool
) -> None:
    source = make_product_source(version=2)
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "delete_item",
            service_error_code="ConditionalCheckFailedException",
            expected_params=_delete_request(expected_version=1),
        )
        response = {} if missing else {"Item": serialize_item(product_source_to_item(source))}
        stubber.add_response("get_item", response, _get_request(PRODUCT_ID, SOURCE_ID))
        repository = DynamoDBProductSourceRepository(dynamodb_client, TABLE_NAME)
        expected_error = (
            ProductSourceNotFoundError if missing else ProductSourceVersionConflictError
        )
        with pytest.raises(expected_error):
            repository.delete(PRODUCT_ID, SOURCE_ID, expected_version=1)


@pytest.mark.parametrize("operation", ["create", "get", "list", "update", "delete"])
def test_repository_wraps_boto_failures(dynamodb_client: BaseClient, operation: str) -> None:
    source = make_product_source()
    method_names = {
        "create": ("put_item", _create_request(source)),
        "get": ("get_item", _get_request(PRODUCT_ID, SOURCE_ID)),
        "list": ("query", _query_request(limit=25)),
        "update": ("update_item", _update_request(source, expected_version=1)),
        "delete": ("delete_item", _delete_request(expected_version=1)),
    }
    method, expected = method_names[operation]
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            method,
            service_error_code="InternalServerError",
            expected_params=expected,
        )
        repository = DynamoDBProductSourceRepository(
            dynamodb_client, TABLE_NAME, clock=lambda: SOURCE_UPDATED_AT
        )
        with pytest.raises(ProductSourceRepositoryError):
            if operation == "create":
                repository.create(source)
            elif operation == "get":
                repository.get_by_id(PRODUCT_ID, SOURCE_ID)
            elif operation == "list":
                repository.list_by_product(PRODUCT_ID)
            elif operation == "update":
                repository.update(source, expected_version=1)
            else:
                repository.delete(PRODUCT_ID, SOURCE_ID, expected_version=1)


def _create_request(source: ProductSource) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "Item": serialize_item(product_source_to_item(source)),
        "ConditionExpression": (
            "attribute_not_exists(#productId) AND attribute_not_exists(#sourceId)"
        ),
        "ExpressionAttributeNames": {"#productId": "productId", "#sourceId": "sourceId"},
    }


def _get_request(product_id: object, source_id: object) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "Key": serialize_item({"productId": product_id, "sourceId": source_id}),
        "ConsistentRead": True,
    }


def _query_request(*, limit: int) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "IndexName": PRODUCT_CREATED_AT_INDEX,
        "KeyConditionExpression": "#productId = :productId",
        "ExpressionAttributeNames": {"#productId": "productId"},
        "ExpressionAttributeValues": serialize_item({":productId": PRODUCT_ID}),
        "ScanIndexForward": False,
        "Limit": limit,
    }


def _update_request(source: ProductSource, expected_version: int) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "Key": serialize_item({"productId": source.product_id, "sourceId": source.source_id}),
        "UpdateExpression": (
            "SET #status = :status, #storageKey = :storageKey, #mimeType = :mimeType, "
            "#fileSizeBytes = :fileSizeBytes, #checksumSha256 = :checksumSha256, "
            "#displayName = :displayName, #textContent = :textContent, "
            "#errorMessage = :errorMessage, #updatedAt = :updatedAt, "
            "#version = :newVersion"
        ),
        "ConditionExpression": (
            "attribute_exists(#productId) AND attribute_exists(#sourceId) "
            "AND #version = :expectedVersion"
        ),
        "ExpressionAttributeNames": {
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
        "ExpressionAttributeValues": serialize_item(
            {
                ":status": source.status,
                ":storageKey": source.storage_key,
                ":mimeType": source.mime_type,
                ":fileSizeBytes": source.file_size_bytes,
                ":checksumSha256": source.checksum_sha256,
                ":displayName": source.display_name,
                ":textContent": source.text_content,
                ":errorMessage": source.error_message,
                ":updatedAt": SOURCE_UPDATED_AT,
                ":newVersion": expected_version + 1,
                ":expectedVersion": expected_version,
            }
        ),
        "ReturnValues": "ALL_NEW",
    }


def _delete_request(expected_version: int) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "Key": serialize_item({"productId": PRODUCT_ID, "sourceId": SOURCE_ID}),
        "ConditionExpression": (
            "attribute_exists(#productId) AND attribute_exists(#sourceId) "
            "AND #version = :expectedVersion"
        ),
        "ExpressionAttributeNames": {
            "#productId": "productId",
            "#sourceId": "sourceId",
            "#version": "version",
        },
        "ExpressionAttributeValues": serialize_item({":expectedVersion": expected_version}),
    }
