"""Opt-in DynamoDB Local category-schema persistence and bootstrap contract."""

import os

import pytest

from app.api.dependencies.dynamodb import create_dynamodb_client
from app.core.config import get_settings
from app.core.exceptions import CategoryAttributeSchemaAlreadyExistsError
from app.domain.category_schemas.builtins import built_in_category_schemas
from app.repositories.dynamodb_category_schemas import (
    DynamoDBCategoryAttributeSchemaRepository,
)
from app.services.category_schemas import CategoryAttributeSchemaService
from app.utils.dynamodb import serialize_item

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DYNAMODB_INTEGRATION") != "1",
    reason="set RUN_DYNAMODB_INTEGRATION=1 after creating category-attribute-schemas",
)


def test_category_schema_contract_against_dynamodb_local() -> None:
    settings = get_settings()
    client = create_dynamodb_client(settings)
    table_name = settings.table_name("category-attribute-schemas")
    repository = DynamoDBCategoryAttributeSchemaRepository(client, table_name)
    service = CategoryAttributeSchemaService(repository)
    schemas = built_in_category_schemas()
    try:
        assert service.seed_builtins() == schemas
        assert service.seed_builtins() == ()
        for schema in schemas:
            assert service.get_active_schema(category=schema.category) == schema
            assert service.get_schema(category=schema.category, version=1) == schema
            with pytest.raises(CategoryAttributeSchemaAlreadyExistsError):
                repository.create(schema)
    finally:
        for schema in schemas:
            client.delete_item(
                TableName=table_name,
                Key=serialize_item({"category": schema.category, "version": schema.version}),
            )
