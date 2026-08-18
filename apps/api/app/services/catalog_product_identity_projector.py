"""Snapshot existing Product identity and derive identity readiness reasons."""

from dataclasses import dataclass

from app.core.exceptions import CatalogProjectionProductTextLimitExceededError
from app.domain.catalog_projection import (
    CatalogBlockingReason,
    CatalogWarningReason,
    ProductIdentitySnapshot,
)
from app.domain.products import Product, ProductCategory


@dataclass(frozen=True, slots=True)
class ProductIdentityProjection:
    identity: ProductIdentitySnapshot
    blockers: tuple[CatalogBlockingReason, ...]
    warnings: tuple[CatalogWarningReason, ...]


class CatalogProductIdentityProjector:
    def __init__(self, *, max_text_characters: int = 50_000) -> None:
        self._max_text = max_text_characters

    def project(self, product: Product) -> ProductIdentityProjection:
        values = (product.name, product.manufacturer, product.model_number, product.description)
        if sum(len(value) for value in values if value is not None) > self._max_text:
            raise CatalogProjectionProductTextLimitExceededError()
        blockers: list[CatalogBlockingReason] = []
        warnings: list[CatalogWarningReason] = []
        if not product.name.strip():
            blockers.append(CatalogBlockingReason.PRODUCT_NAME_MISSING)
        if product.category is ProductCategory.UNCLASSIFIED:
            blockers.append(CatalogBlockingReason.PRODUCT_CATEGORY_UNCLASSIFIED)
        if product.manufacturer is None:
            warnings.append(CatalogWarningReason.MANUFACTURER_MISSING)
        if product.model_number is None:
            warnings.append(CatalogWarningReason.MODEL_NUMBER_MISSING)
        if product.description is None:
            warnings.append(CatalogWarningReason.DESCRIPTION_MISSING)
        return ProductIdentityProjection(
            identity=ProductIdentitySnapshot(
                product_id=product.product_id,
                product_version=product.version,
                product_name=product.name,
                manufacturer=product.manufacturer,
                model_number=product.model_number,
                category=product.category,
                description=product.description,
            ),
            blockers=tuple(blockers),
            warnings=tuple(warnings),
        )
