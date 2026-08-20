"""Idempotently seed built-in schemas into DynamoDB Local for development."""

import logging

from app.api.dependencies.dynamodb import create_dynamodb_client
from app.core.config import get_settings
from app.repositories.dynamodb_category_schemas import (
    DynamoDBCategoryAttributeSchemaRepository,
)
from app.services.category_schemas import CategoryAttributeSchemaService


def seed_category_attribute_schemas() -> int:
    settings = get_settings()
    if settings.app_env == "production" or not settings.dynamodb_endpoint_url:
        raise RuntimeError(
            "category schema seeding is limited to configured local development"
        )
    client = create_dynamodb_client(settings)
    repository = DynamoDBCategoryAttributeSchemaRepository(
        client, settings.table_name("category-attribute-schemas")
    )
    service = CategoryAttributeSchemaService(
        repository,
        max_attributes=settings.category_attribute_schema_max_attributes,
        max_aliases_per_attribute=(
            settings.category_attribute_schema_max_aliases_per_attribute
        ),
    )
    seeded = service.seed_builtins()
    logging.getLogger(__name__).info(
        "Seeded %s category attribute schemas", len(seeded)
    )
    return len(seeded)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    seed_category_attribute_schemas()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
