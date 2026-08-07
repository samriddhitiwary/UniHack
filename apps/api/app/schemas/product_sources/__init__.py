"""Product-source boundary schemas."""

from app.schemas.product_sources.models import (
    ProductSourceCreate,
    ProductSourceListResult,
    ProductSourceRecord,
    ProductSourceUpdate,
    TextProductSourceCreate,
)

__all__ = [
    "ProductSourceCreate",
    "ProductSourceListResult",
    "ProductSourceRecord",
    "ProductSourceUpdate",
    "TextProductSourceCreate",
]
