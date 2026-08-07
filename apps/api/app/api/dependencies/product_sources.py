"""Product-source repository and service dependency providers."""

from typing import Annotated

from botocore.client import BaseClient
from fastapi import Depends

from app.api.dependencies.dynamodb import get_dynamodb_client
from app.api.dependencies.products import get_product_repository
from app.core.config import Settings, get_settings
from app.repositories.dynamodb_product_sources import DynamoDBProductSourceRepository
from app.repositories.product_sources import ProductSourceRepository
from app.repositories.products import ProductRepository
from app.services.product_sources import ProductSourceService
from app.storage.dependencies import get_object_storage
from app.storage.protocol import ObjectStorage
from app.utils.file_validation import UploadSizeLimits


def get_product_source_repository(
    client: Annotated[BaseClient, Depends(get_dynamodb_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProductSourceRepository:
    """Build the configured product-source repository."""
    return DynamoDBProductSourceRepository(client, settings.table_name("sources"))


def get_product_source_service(
    product_repository: Annotated[ProductRepository, Depends(get_product_repository)],
    source_repository: Annotated[ProductSourceRepository, Depends(get_product_source_repository)],
    object_storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProductSourceService:
    """Build the focused product-source application service."""
    limits = UploadSizeLimits(
        pdf=settings.max_pdf_upload_bytes,
        image=settings.max_image_upload_bytes,
        csv=settings.max_csv_upload_bytes,
    )
    return ProductSourceService(product_repository, source_repository, object_storage, limits)
