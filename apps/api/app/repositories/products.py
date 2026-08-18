"""Product repository contract."""

from typing import Protocol
from uuid import UUID

from app.domain.products import Product, ProductPage, ProductStatus


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

    def delete(self, product_id: UUID, expected_version: int) -> None: ...
