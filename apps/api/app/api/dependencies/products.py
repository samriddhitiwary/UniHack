"""Product repository and service dependency providers."""

from typing import Annotated

from botocore.client import BaseClient
from fastapi import Depends

from app.api.dependencies.dynamodb import get_dynamodb_client
from app.core.config import Settings, get_settings
from app.repositories.dynamodb_products import DynamoDBProductRepository
from app.repositories.products import ProductRepository
from app.services.products import ProductService


def get_product_repository(
    client: Annotated[BaseClient, Depends(get_dynamodb_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProductRepository:
    """Build the configured product repository for the current environment."""
    return DynamoDBProductRepository(client, settings.table_name("products"))


def get_product_service(
    repository: Annotated[ProductRepository, Depends(get_product_repository)],
) -> ProductService:
    """Build the product application service."""
    return ProductService(repository)
