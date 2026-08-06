"""Product-source boundary schemas."""

from app.schemas.product_sources.models import (
    ProductSourceCreate,
    ProductSourceListResult,
    ProductSourceRecord,
    ProductSourceUpdate,
)

__all__ = [
    "ProductSourceCreate",
    "ProductSourceListResult",
    "ProductSourceRecord",
    "ProductSourceUpdate",
]
