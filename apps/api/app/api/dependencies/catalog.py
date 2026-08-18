"""Catalog projection and publishing-readiness dependency providers."""

from typing import Annotated

from botocore.client import BaseClient
from fastapi import Depends

from app.api.dependencies.dynamodb import get_dynamodb_client
from app.api.dependencies.products import get_product_repository
from app.core.config import Settings, get_settings
from app.repositories.catalog_projection import CommerceCatalogProjectionRepository
from app.repositories.dynamodb_catalog_projection import (
    DynamoDBCommerceCatalogProjectionRepository,
)
from app.repositories.products import ProductRepository
from app.services.publishing_readiness_application import (
    PublishingReadinessApplicationService,
)


def get_catalog_projection_repository(
    client: Annotated[BaseClient, Depends(get_dynamodb_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CommerceCatalogProjectionRepository:
    return DynamoDBCommerceCatalogProjectionRepository(
        client, settings.table_name("catalog-projection-results")
    )


def get_publishing_readiness_service(
    product_repository: Annotated[ProductRepository, Depends(get_product_repository)],
    projection_repository: Annotated[
        CommerceCatalogProjectionRepository, Depends(get_catalog_projection_repository)
    ],
) -> PublishingReadinessApplicationService:
    return PublishingReadinessApplicationService(product_repository, projection_repository)
