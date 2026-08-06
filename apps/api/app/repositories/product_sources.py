"""Product-source repository contract."""

from typing import Protocol
from uuid import UUID

from app.domain.product_sources import ProductSource, ProductSourcePage


class ProductSourceRepository(Protocol):
    def create(self, source: ProductSource) -> ProductSource: ...

    def get_by_id(self, product_id: UUID, source_id: UUID) -> ProductSource | None: ...

    def update(self, source: ProductSource, expected_version: int) -> ProductSource: ...

    def list_by_product(
        self,
        product_id: UUID,
        *,
        limit: int = 25,
        cursor: str | None = None,
    ) -> ProductSourcePage: ...

    def delete(self, product_id: UUID, source_id: UUID, expected_version: int) -> None: ...
