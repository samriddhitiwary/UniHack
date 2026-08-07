"""Processing-job repository and service dependency providers."""

from typing import Annotated

from botocore.client import BaseClient
from fastapi import Depends

from app.api.dependencies.dynamodb import get_dynamodb_client
from app.api.dependencies.product_sources import get_product_source_repository
from app.api.dependencies.products import get_product_repository
from app.core.config import Settings, get_settings
from app.repositories.dynamodb_processing_jobs import DynamoDBProcessingJobRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_sources import ProductSourceRepository
from app.repositories.products import ProductRepository
from app.services.processing_jobs import ProcessingJobService


def get_processing_job_repository(
    client: Annotated[BaseClient, Depends(get_dynamodb_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProcessingJobRepository:
    """Build the configured processing-job repository."""
    return DynamoDBProcessingJobRepository(client, settings.table_name("processing-jobs"))


def get_processing_job_service(
    product_repository: Annotated[ProductRepository, Depends(get_product_repository)],
    source_repository: Annotated[ProductSourceRepository, Depends(get_product_source_repository)],
    job_repository: Annotated[ProcessingJobRepository, Depends(get_processing_job_repository)],
) -> ProcessingJobService:
    """Build the processing-job application service."""
    return ProcessingJobService(product_repository, source_repository, job_repository)
