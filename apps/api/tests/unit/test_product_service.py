"""Product application service tests."""

import inspect
from typing import cast

import pytest

from app.core.exceptions import (
    InvalidProductCursorError,
    ProductAlreadyExistsError,
    ProductNotFoundError,
    ProductRepositoryError,
)
from app.domain.products import Product, ProductCategory, ProductPage, ProductStatus
from app.repositories.products import ProductRepository
from app.schemas.products import ProductCreate
from app.services import products as products_module
from app.services.products import ProductService
from tests.fixtures.products import PRODUCT_ID, make_product


class FakeProductRepository:
    def __init__(
        self,
        product: Product | None = None,
        error: Exception | None = None,
        page: ProductPage | None = None,
    ) -> None:
        self.product = product
        self.error = error
        self.page = page or ProductPage(items=(), next_cursor=None)
        self.created: list[Product] = []
        self.requested_ids = []
        self.list_calls: list[tuple[int, str | None]] = []
        self.status_list_calls: list[tuple[ProductStatus, int, str | None]] = []

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

    def list_products(self, *, limit: int, cursor: str | None = None) -> ProductPage:
        self.list_calls.append((limit, cursor))
        if self.error is not None:
            raise self.error
        return self.page

    def list_by_status(
        self,
        status: ProductStatus,
        *,
        limit: int,
        cursor: str | None = None,
    ) -> ProductPage:
        self.status_list_calls.append((status, limit, cursor))
        if self.error is not None:
            raise self.error
        return self.page


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


def test_list_products_uses_unfiltered_repository_and_returns_public_records() -> None:
    product = make_product()
    repository = FakeProductRepository(page=ProductPage(items=(product,), next_cursor="next-page"))

    result = _service(repository).list_products(limit=12, cursor="current-page")

    assert repository.list_calls == [(12, "current-page")]
    assert repository.status_list_calls == []
    assert [item.product_id for item in result.items] == [product.product_id]
    assert result.next_cursor == "next-page"


def test_list_products_uses_only_status_repository_when_status_is_present() -> None:
    repository = FakeProductRepository()

    result = _service(repository).list_products(
        limit=5,
        cursor="status-page",
        status=ProductStatus.REVIEW_REQUIRED,
    )

    assert repository.list_calls == []
    assert repository.status_list_calls == [(ProductStatus.REVIEW_REQUIRED, 5, "status-page")]
    assert result.items == []
    assert result.next_cursor is None


@pytest.mark.parametrize(
    "error_type",
    [InvalidProductCursorError, ProductRepositoryError],
)
def test_list_products_preserves_controlled_repository_errors(
    error_type: type[ProductRepositoryError],
) -> None:
    error = error_type("repository detail")
    service = _service(FakeProductRepository(error=error))

    with pytest.raises(error_type) as captured:
        service.list_products(limit=20)

    assert captured.value is error


def test_service_module_has_no_fastapi_dependency() -> None:
    assert "fastapi" not in inspect.getsource(products_module)
