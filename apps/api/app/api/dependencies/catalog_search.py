"""Catalog search, summary, and quality-read dependency providers."""

from typing import Annotated

from botocore.client import BaseClient
from fastapi import Depends

from app.api.dependencies.catalog import get_catalog_projection_repository
from app.api.dependencies.dynamodb import get_dynamodb_client
from app.api.dependencies.products import get_product_repository
from app.core.config import Settings, get_settings
from app.repositories.catalog_enrichment import CatalogEnrichmentResultRepository
from app.repositories.catalog_export import CatalogExportResultRepository
from app.repositories.catalog_projection import CommerceCatalogProjectionRepository
from app.repositories.dynamodb_catalog_enrichment import DynamoDBCatalogEnrichmentResultRepository
from app.repositories.dynamodb_catalog_export import DynamoDBCatalogExportResultRepository
from app.repositories.dynamodb_product_intelligence import (
    DynamoDBProductIntelligenceScoreRepository,
)
from app.repositories.product_intelligence import ProductIntelligenceScoreRepository
from app.repositories.products import ProductRepository
from app.services.catalog_search import CatalogSearchService
from app.services.catalog_summary import CatalogSummaryService
from app.services.product_intelligence_read import ProductIntelligenceReadService


def get_product_intelligence_score_repository(
    client: Annotated[BaseClient, Depends(get_dynamodb_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProductIntelligenceScoreRepository:
    return DynamoDBProductIntelligenceScoreRepository(
        client, settings.table_name("product-intelligence-score-results")
    )


def get_catalog_enrichment_repository(
    client: Annotated[BaseClient, Depends(get_dynamodb_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CatalogEnrichmentResultRepository:
    return DynamoDBCatalogEnrichmentResultRepository(
        client, settings.table_name("catalog-enrichment-results")
    )


def get_catalog_export_repository(
    client: Annotated[BaseClient, Depends(get_dynamodb_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CatalogExportResultRepository:
    return DynamoDBCatalogExportResultRepository(
        client, settings.table_name("catalog-export-results")
    )


def get_catalog_summary_service(
    product_repository: Annotated[ProductRepository, Depends(get_product_repository)],
    projection_repository: Annotated[
        CommerceCatalogProjectionRepository, Depends(get_catalog_projection_repository)
    ],
    score_repository: Annotated[
        ProductIntelligenceScoreRepository,
        Depends(get_product_intelligence_score_repository),
    ],
    enrichment_repository: Annotated[
        CatalogEnrichmentResultRepository, Depends(get_catalog_enrichment_repository)
    ],
    export_repository: Annotated[
        CatalogExportResultRepository, Depends(get_catalog_export_repository)
    ],
) -> CatalogSummaryService:
    return CatalogSummaryService(
        product_repository=product_repository,
        projection_repository=projection_repository,
        score_repository=score_repository,
        enrichment_repository=enrichment_repository,
        export_repository=export_repository,
    )


def get_catalog_search_service(
    product_repository: Annotated[ProductRepository, Depends(get_product_repository)],
    summary_service: Annotated[CatalogSummaryService, Depends(get_catalog_summary_service)],
) -> CatalogSearchService:
    return CatalogSearchService(product_repository, summary_service)


def get_product_intelligence_read_service(
    product_repository: Annotated[ProductRepository, Depends(get_product_repository)],
    score_repository: Annotated[
        ProductIntelligenceScoreRepository,
        Depends(get_product_intelligence_score_repository),
    ],
) -> ProductIntelligenceReadService:
    return ProductIntelligenceReadService(product_repository, score_repository)
