"""Category-attribute-schema repository contract."""

from typing import Protocol

from app.domain.category_schemas import CategoryAttributeSchema
from app.domain.products import ProductCategory


class CategoryAttributeSchemaRepository(Protocol):
    def create(self, schema: CategoryAttributeSchema) -> CategoryAttributeSchema: ...

    def get_by_category_and_version(
        self, category: ProductCategory, version: int
    ) -> CategoryAttributeSchema | None: ...

    def get_active_by_category(
        self, category: ProductCategory
    ) -> CategoryAttributeSchema | None: ...
