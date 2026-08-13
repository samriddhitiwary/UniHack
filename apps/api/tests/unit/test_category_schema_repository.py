"""DynamoDB category-schema repository tests."""

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.core.exceptions import (
    CategoryAttributeSchemaAlreadyExistsError,
    CategoryAttributeSchemaItemTooLargeError,
    CategoryAttributeSchemaNotAvailableError,
    CategoryAttributeSchemaRepositoryError,
)
from app.domain.category_schemas.builtins import (
    centrifugal_pump_schema_v1,
    induction_motor_schema_v1,
)
from app.domain.products import ProductCategory
from app.repositories import dynamodb_category_schemas as repository_module
from app.repositories.dynamodb_category_schemas import (
    DynamoDBCategoryAttributeSchemaRepository,
)
from app.utils.dynamodb import category_attribute_schema_to_item, serialize_item


def conditional_error() -> ClientError:
    return ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")


def test_create_is_conditional_and_never_overwrites() -> None:
    schema = induction_motor_schema_v1()
    client = MagicMock()
    client.query.return_value = {"Items": []}
    repository = DynamoDBCategoryAttributeSchemaRepository(client, "schemas")
    assert repository.create(schema) == schema
    call = client.put_item.call_args.kwargs
    assert "attribute_not_exists" in call["ConditionExpression"]
    assert call["Item"]["category"] == {"S": "INDUCTION_MOTOR"}
    client.put_item.side_effect = conditional_error()
    with pytest.raises(CategoryAttributeSchemaAlreadyExistsError):
        repository.create(schema)


def test_create_rejects_a_second_active_version() -> None:
    active = induction_motor_schema_v1()
    candidate = induction_motor_schema_v1()
    candidate = type(candidate).create(
        category=candidate.category,
        version=2,
        status=candidate.status,
        description=candidate.description,
        attributes=candidate.attributes,
        now=candidate.created_at,
    )
    client = MagicMock()
    client.query.return_value = {
        "Items": [serialize_item(category_attribute_schema_to_item(active))]
    }
    repository = DynamoDBCategoryAttributeSchemaRepository(client, "schemas")
    with pytest.raises(CategoryAttributeSchemaAlreadyExistsError):
        repository.create(candidate)
    client.put_item.assert_not_called()


def test_retrieve_by_category_version_and_missing() -> None:
    schema = centrifugal_pump_schema_v1()
    client = MagicMock()
    client.get_item.return_value = {
        "Item": serialize_item(category_attribute_schema_to_item(schema))
    }
    repository = DynamoDBCategoryAttributeSchemaRepository(client, "schemas")
    assert repository.get_by_category_and_version(schema.category, 1) == schema
    assert client.get_item.call_args.kwargs["ConsistentRead"] is True
    client.get_item.return_value = {}
    assert repository.get_by_category_and_version(schema.category, 2) is None


def test_active_lookup_is_bounded_descending_and_uses_no_scan() -> None:
    inactive = type(induction_motor_schema_v1()).create(
        category=ProductCategory.INDUCTION_MOTOR,
        version=2,
        status=repository_module.CategoryAttributeSchemaStatus.INACTIVE,
        description="Inactive test schema.",
        attributes=induction_motor_schema_v1().attributes,
    )
    active = induction_motor_schema_v1()
    client = MagicMock()
    client.query.return_value = {
        "Items": [
            serialize_item(category_attribute_schema_to_item(inactive)),
            serialize_item(category_attribute_schema_to_item(active)),
        ]
    }
    repository = DynamoDBCategoryAttributeSchemaRepository(client, "schemas")
    assert repository.get_active_by_category(ProductCategory.INDUCTION_MOTOR) == active
    request = client.query.call_args.kwargs
    assert request["ScanIndexForward"] is False and request["Limit"] == 100
    client.scan.assert_not_called()


def test_unclassified_and_repository_failures_are_controlled() -> None:
    repository = DynamoDBCategoryAttributeSchemaRepository(MagicMock(), "schemas")
    with pytest.raises(CategoryAttributeSchemaNotAvailableError):
        repository.get_active_by_category(ProductCategory.UNCLASSIFIED)
    repository._client.get_item.side_effect = ClientError(
        {"Error": {"Code": "Internal"}}, "GetItem"
    )
    with pytest.raises(CategoryAttributeSchemaRepositoryError):
        repository.get_by_category_and_version(ProductCategory.INDUCTION_MOTOR, 1)


def test_item_size_guard_runs_before_write(monkeypatch) -> None:
    client = MagicMock()
    client.query.return_value = {"Items": []}
    monkeypatch.setattr(repository_module, "MAX_SAFE_ITEM_BYTES", 1)
    with pytest.raises(CategoryAttributeSchemaItemTooLargeError):
        DynamoDBCategoryAttributeSchemaRepository(client, "schemas").create(
            induction_motor_schema_v1()
        )
    client.put_item.assert_not_called()
