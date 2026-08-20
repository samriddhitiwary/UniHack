"""Product repository contract."""

from typing import Protocol
from uuid import UUID

from app.domain.products import Product, ProductCategory, ProductPage, ProductStatus


class ProductRepository(Protocol):
    """Persistence-independent product operations used by future services."""

    def create(self, product: Product) -> Product: ...

    def get_by_id(self, product_id: UUID) -> Product | None: ...

    def update(self, product: Product, expected_version: int) -> Product: ...

    def mark_ready_to_publish(
        self,
        *,
        product_id: UUID,
        expected_version: int,
        expected_status: ProductStatus,
    ) -> Product: ...

    def list_products(self, *, limit: int = 25, cursor: str | None = None) -> ProductPage: ...

    def list_by_status(
        self, status: ProductStatus, *, limit: int = 25, cursor: str | None = None
    ) -> ProductPage: ...

    def list_created(self, *, limit: int = 20, cursor: str | None = None) -> ProductPage: ...
    def search_by_status(
        self, status: ProductStatus, *, limit: int = 20, cursor: str | None = None
    ) -> ProductPage: ...
    def list_by_category(
        self, category: ProductCategory, *, limit: int = 20, cursor: str | None = None
    ) -> ProductPage: ...
    def list_by_category_status(
        self,
        category: ProductCategory,
        status: ProductStatus,
        *,
        limit: int = 20,
        cursor: str | None = None,
    ) -> ProductPage: ...
    def list_by_manufacturer(
        self, normalized_manufacturer: str, *, limit: int = 20, cursor: str | None = None
    ) -> ProductPage: ...
    def list_by_model_number(
        self, normalized_model_number: str, *, limit: int = 20, cursor: str | None = None
    ) -> ProductPage: ...
    def list_by_name_prefix(
        self, normalized_prefix: str, *, limit: int = 20, cursor: str | None = None
    ) -> ProductPage: ...

    def delete(self, product_id: UUID, expected_version: int) -> None: ...
