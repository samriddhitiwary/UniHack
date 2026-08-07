"""Product-source application service tests."""

import hashlib
import inspect
from typing import cast
from uuid import UUID

import pytest

from app.core.exceptions import (
    ProductNotFoundError,
    ProductRepositoryError,
    ProductSourceAlreadyExistsError,
    ProductSourceRepositoryError,
)
from app.domain.product_sources import (
    ProductSource,
    ProductSourcePage,
    ProductSourceStatus,
    ProductSourceType,
)
from app.domain.products import Product, ProductPage, ProductStatus
from app.repositories.product_sources import ProductSourceRepository
from app.repositories.products import ProductRepository
from app.schemas.product_sources import TextProductSourceCreate
from app.services import product_sources as product_sources_module
from app.services.product_sources import ProductSourceService
from tests.fixtures.products import PRODUCT_ID, make_product


class FakeProductRepository:
    def __init__(self, product: Product | None = None, error: Exception | None = None) -> None:
        self.product = product
        self.error = error
        self.requested_ids: list[UUID] = []

    def get_by_id(self, product_id: UUID) -> Product | None:
        self.requested_ids.append(product_id)
        if self.error is not None:
            raise self.error
        return self.product

    def create(self, product: Product) -> Product:
        raise NotImplementedError

    def update(self, product: Product, expected_version: int) -> Product:
        raise NotImplementedError

    def list_products(self, *, limit: int = 25, cursor: str | None = None) -> ProductPage:
        raise NotImplementedError

    def list_by_status(
        self, status: ProductStatus, *, limit: int = 25, cursor: str | None = None
    ) -> ProductPage:
        raise NotImplementedError

    def delete(self, product_id: UUID, expected_version: int) -> None:
        raise NotImplementedError


class FakeProductSourceRepository:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.created: list[ProductSource] = []

    def create(self, source: ProductSource) -> ProductSource:
        self.created.append(source)
        if self.error is not None:
            raise self.error
        return source

    def get_by_id(self, product_id: UUID, source_id: UUID) -> ProductSource | None:
        raise NotImplementedError

    def update(self, source: ProductSource, expected_version: int) -> ProductSource:
        raise NotImplementedError

    def list_by_product(
        self,
        product_id: UUID,
        *,
        limit: int = 25,
        cursor: str | None = None,
    ) -> ProductSourcePage:
        raise NotImplementedError

    def delete(self, product_id: UUID, source_id: UUID, expected_version: int) -> None:
        raise NotImplementedError


def service(
    products: FakeProductRepository, sources: FakeProductSourceRepository
) -> ProductSourceService:
    return ProductSourceService(
        cast(ProductRepository, products), cast(ProductSourceRepository, sources)
    )


def test_create_text_source_checks_parent_and_builds_ready_metadata() -> None:
    products = FakeProductRepository(product=make_product())
    sources = FakeProductSourceRepository()
    request = TextProductSourceCreate(
        displayName="  Supplier notes  ",
        textContent="  Café pump\nPressure: 16 bar  ",
    )

    created = service(products, sources).create_text_source(PRODUCT_ID, request)

    normalized = "Café pump\nPressure: 16 bar"
    encoded = normalized.encode("utf-8")
    assert products.requested_ids == [PRODUCT_ID]
    assert sources.created == [created]
    assert created.product_id == PRODUCT_ID
    assert created.source_type is ProductSourceType.TEXT
    assert created.status is ProductSourceStatus.READY
    assert created.original_filename is None
    assert created.storage_key is None
    assert created.mime_type == "text/plain"
    assert created.file_size_bytes == len(encoded)
    assert created.checksum_sha256 == hashlib.sha256(encoded).hexdigest()
    assert created.display_name == "Supplier notes"
    assert created.text_content == normalized
    assert created.error_message is None
    assert created.version == 1
    assert created.source_id is not None
    assert created.created_at == created.updated_at


def test_empty_display_name_is_normalized_to_none() -> None:
    sources = FakeProductSourceRepository()
    request = TextProductSourceCreate(displayName="   ", textContent=" Model PX-400 ")
    created = service(FakeProductRepository(product=make_product()), sources).create_text_source(
        PRODUCT_ID, request
    )
    assert created.display_name is None
    assert created.text_content == "Model PX-400"


def test_missing_product_stops_before_source_repository() -> None:
    products = FakeProductRepository()
    sources = FakeProductSourceRepository()

    with pytest.raises(ProductNotFoundError) as captured:
        service(products, sources).create_text_source(
            PRODUCT_ID, TextProductSourceCreate(textContent="Model PX-400")
        )

    assert captured.value.product_id == str(PRODUCT_ID)
    assert products.requested_ids == [PRODUCT_ID]
    assert sources.created == []


def test_product_repository_failure_is_preserved_without_source_create() -> None:
    error = ProductRepositoryError("private product persistence detail")
    products = FakeProductRepository(error=error)
    sources = FakeProductSourceRepository()

    with pytest.raises(ProductRepositoryError) as captured:
        service(products, sources).create_text_source(
            PRODUCT_ID, TextProductSourceCreate(textContent="Model PX-400")
        )

    assert captured.value is error
    assert sources.created == []


@pytest.mark.parametrize(
    "error",
    [
        ProductSourceAlreadyExistsError("duplicate"),
        ProductSourceRepositoryError("private source persistence detail"),
    ],
)
def test_source_repository_controlled_failure_is_preserved(error: Exception) -> None:
    sources = FakeProductSourceRepository(error=error)

    with pytest.raises(type(error)) as captured:
        service(FakeProductRepository(product=make_product()), sources).create_text_source(
            PRODUCT_ID, TextProductSourceCreate(textContent="Model PX-400")
        )

    assert captured.value is error
    assert len(sources.created) == 1


def test_service_has_no_http_boto3_filesystem_or_object_storage_dependency() -> None:
    source = inspect.getsource(product_sources_module)
    assert "fastapi" not in source
    assert "boto3" not in source
    assert "pathlib" not in source
    assert "app.storage" not in source
    assert "open(" not in source
