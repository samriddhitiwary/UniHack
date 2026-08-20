"""Dependency graph for the synchronous Catalog Intelligence workflow."""

from typing import Annotated

from botocore.client import BaseClient
from fastapi import Depends

from app.api.dependencies.catalog import get_catalog_projection_repository
from app.api.dependencies.dynamodb import get_dynamodb_client
from app.api.dependencies.processing_jobs import get_processing_job_repository
from app.api.dependencies.product_reviews import (
    get_product_review_repository,
    get_product_review_service,
)
from app.api.dependencies.product_sources import get_product_source_repository
from app.api.dependencies.products import get_product_repository
from app.core.config import Settings, get_settings
from app.repositories.catalog_projection import CommerceCatalogProjectionRepository
from app.repositories.catalog_workflow import CatalogIntelligenceWorkflowRepository
from app.repositories.dynamodb_catalog_workflow import (
    DynamoDBCatalogIntelligenceWorkflowRepository,
)
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_review import ProductReviewRepository
from app.repositories.product_sources import ProductSourceRepository
from app.repositories.products import ProductRepository
from app.services.catalog_workflow_orchestrator import (
    CatalogIntelligenceWorkflowService,
    CatalogWorkflowStageExecutor,
)
from app.services.catalog_workflow_runtime import build_catalog_workflow_stage_executor
from app.services.product_review import ProductReviewService
from app.storage.dependencies import get_object_storage
from app.storage.protocol import ObjectStorage


def get_catalog_workflow_repository(
    client: Annotated[BaseClient, Depends(get_dynamodb_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CatalogIntelligenceWorkflowRepository:
    return DynamoDBCatalogIntelligenceWorkflowRepository(
        client, settings.table_name("catalog-intelligence-workflows")
    )


def get_catalog_workflow_stage_executor(
    client: Annotated[BaseClient, Depends(get_dynamodb_client)],
    settings: Annotated[Settings, Depends(get_settings)],
    jobs: Annotated[ProcessingJobRepository, Depends(get_processing_job_repository)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    sources: Annotated[ProductSourceRepository, Depends(get_product_source_repository)],
    reviews: Annotated[ProductReviewRepository, Depends(get_product_review_repository)],
    projections: Annotated[
        CommerceCatalogProjectionRepository, Depends(get_catalog_projection_repository)
    ],
    review_service: Annotated[ProductReviewService, Depends(get_product_review_service)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
) -> CatalogWorkflowStageExecutor:
    return build_catalog_workflow_stage_executor(
        client=client,
        settings=settings,
        jobs=jobs,
        products=products,
        sources=sources,
        reviews=reviews,
        projections=projections,
        review_service=review_service,
        storage=storage,
    )


def get_catalog_workflow_service(
    workflows: Annotated[
        CatalogIntelligenceWorkflowRepository, Depends(get_catalog_workflow_repository)
    ],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    sources: Annotated[ProductSourceRepository, Depends(get_product_source_repository)],
    executor: Annotated[CatalogWorkflowStageExecutor, Depends(get_catalog_workflow_stage_executor)],
) -> CatalogIntelligenceWorkflowService:
    return CatalogIntelligenceWorkflowService(
        workflow_repository=workflows,
        product_repository=products,
        source_repository=sources,
        executor=executor,
    )
