"""Product application service tests."""

import inspect
from typing import cast

import pytest

from app.core.exceptions import (
    ProductAlreadyExistsError,
    ProductNotFoundError,
    ProductRepositoryError,
)
from app.domain.products import Product, ProductCategory, ProductStatus
from app.repositories.products import ProductRepository
from app.schemas.products import ProductCreate
from app.services import products as products_module
from app.services.products import ProductService
from tests.fixtures.products import PRODUCT_ID, make_product


class FakeProductRepository:
    def __init__(self, product: Product | None = None, error: Exception | None = None) -> None:
        self.product = product
        self.error = error
        self.created: list[Product] = []
        self.requested_ids = []

    def create(self, product: Product) -> Product:
        if self.error is not None:
            raise self.error
        self.created.append(product)
        return product

    def get_by_id(self, product_id: object) -> Product | None:
        if self.error is not None:
            raise self.error
        self.requested_ids.append(product_id)
        return self.product


def _service(repository: FakeProductRepository) -> ProductService:
    return ProductService(cast(ProductRepository, repository))


def test_create_product_applies_defaults_calls_repository_and_returns_product() -> None:
    repository = FakeProductRepository()
    request = ProductCreate(
        name="  PX-400 Pump  ",
        manufacturer="ABC Industries",
        modelNumber="PX-400",
        category=ProductCategory.CENTRIFUGAL_PUMP,
    )

    product = _service(repository).create_product(request)

    assert repository.created == [product]
    assert product.name == "PX-400 Pump"
    assert product.model_number == "PX-400"
    assert product.status is ProductStatus.DRAFT
    assert product.source_count == 0
    assert product.version == 1
    assert product.product_id is not None


def test_create_preserves_duplicate_exception() -> None:
    error = ProductAlreadyExistsError(PRODUCT_ID)
    service = _service(FakeProductRepository(error=error))
    with pytest.raises(ProductAlreadyExistsError) as captured:
        service.create_product(ProductCreate(name="Valid product"))
    assert captured.value is error


def test_get_product_returns_repository_product() -> None:
    product = make_product()
    repository = FakeProductRepository(product=product)
    assert _service(repository).get_product(PRODUCT_ID) == product
    assert repository.requested_ids == [PRODUCT_ID]


def test_get_missing_product_raises_not_found() -> None:
    with pytest.raises(ProductNotFoundError) as captured:
        _service(FakeProductRepository()).get_product(PRODUCT_ID)
    assert captured.value.product_id == str(PRODUCT_ID)


def test_service_preserves_repository_failure() -> None:
    error = ProductRepositoryError("unavailable")
    with pytest.raises(ProductRepositoryError) as captured:
        _service(FakeProductRepository(error=error)).get_product(PRODUCT_ID)
    assert captured.value is error


def test_service_module_has_no_fastapi_dependency() -> None:
    assert "fastapi" not in inspect.getsource(products_module)
