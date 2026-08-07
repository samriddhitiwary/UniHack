"""Product-source dependency construction tests."""

from typing import cast
from unittest.mock import MagicMock

from botocore.client import BaseClient

from app.api.dependencies.product_sources import (
    get_product_source_repository,
    get_product_source_service,
)
from app.core.config import Settings
from app.repositories.dynamodb_product_sources import DynamoDBProductSourceRepository
from app.repositories.product_sources import ProductSourceRepository
from app.repositories.products import ProductRepository
from app.services.product_sources import ProductSourceService
from app.storage.protocol import ObjectStorage
from tests.unit.test_product_source_service import (
    FakeProductRepository,
    FakeProductSourceRepository,
    FakeStorage,
)


def test_repository_provider_uses_configured_sources_table() -> None:
    repository = get_product_source_repository(
        cast(BaseClient, MagicMock()), Settings(dynamodb_table_prefix="catalogiq-test")
    )
    assert isinstance(repository, DynamoDBProductSourceRepository)
    assert repository._table_name == "catalogiq-test-sources"


def test_service_provider_wires_both_repository_protocols() -> None:
    service = get_product_source_service(
        cast(ProductRepository, FakeProductRepository()),
        cast(ProductSourceRepository, FakeProductSourceRepository()),
        cast(ObjectStorage, FakeStorage()),
        Settings(max_pdf_upload_bytes=11, max_image_upload_bytes=12, max_csv_upload_bytes=13),
    )
    assert isinstance(service, ProductSourceService)
    assert service._upload_limits is not None
    assert service._upload_limits.pdf == 11
