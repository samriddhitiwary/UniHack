"""Deterministic product fixtures."""

from datetime import UTC, datetime
from uuid import UUID

from app.domain.products import Product, ProductCategory, ProductStatus

PRODUCT_ID = UUID("d8c8d2bc-3957-4a15-966f-a06da1fd9047")
SECOND_PRODUCT_ID = UUID("92275ab1-75d6-46bf-9a21-afbd1bb87671")
CREATED_AT = datetime(2026, 8, 6, 11, 30, tzinfo=UTC)
UPDATED_AT = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)


def make_product(
    *,
    product_id: UUID = PRODUCT_ID,
    name: str = "PX-400 Centrifugal Pump",
    status: ProductStatus = ProductStatus.DRAFT,
    version: int = 1,
    updated_at: datetime = CREATED_AT,
) -> Product:
    return Product(
        product_id=product_id,
        name=name,
        manufacturer="ABC Industries",
        model_number="PX-400",
        category=ProductCategory.CENTRIFUGAL_PUMP,
        status=status,
        description=None,
        source_count=0,
        created_at=CREATED_AT,
        updated_at=updated_at,
        version=version,
    )
