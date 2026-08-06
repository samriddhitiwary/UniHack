"""Product domain entities and invariants."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from app.domain.products.enums import ProductCategory, ProductStatus

NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 200
MANUFACTURER_MAX_LENGTH = 200
MODEL_NUMBER_MAX_LENGTH = 120
DESCRIPTION_MAX_LENGTH = 4_000


def _required_text(value: str, field: str, minimum: int, maximum: int) -> str:
    normalized = value.strip()
    if len(normalized) < minimum or len(normalized) > maximum:
        raise ValueError(f"{field} must contain between {minimum} and {maximum} characters")
    return normalized


def _optional_text(value: str | None, field: str, maximum: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > maximum:
        raise ValueError(f"{field} must contain at most {maximum} characters")
    return normalized


def _utc_datetime(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class Product:
    product_id: UUID
    name: str
    manufacturer: str | None
    model_number: str | None
    category: ProductCategory
    status: ProductStatus
    description: str | None
    source_count: int
    created_at: datetime
    updated_at: datetime
    version: int

    def __post_init__(self) -> None:
        if not isinstance(self.product_id, UUID):
            raise ValueError("product_id must be a UUID")
        if not isinstance(self.category, ProductCategory):
            raise ValueError("category must be a ProductCategory")
        if not isinstance(self.status, ProductStatus):
            raise ValueError("status must be a ProductStatus")
        object.__setattr__(
            self, "name", _required_text(self.name, "name", NAME_MIN_LENGTH, NAME_MAX_LENGTH)
        )
        object.__setattr__(
            self,
            "manufacturer",
            _optional_text(self.manufacturer, "manufacturer", MANUFACTURER_MAX_LENGTH),
        )
        object.__setattr__(
            self,
            "model_number",
            _optional_text(self.model_number, "model_number", MODEL_NUMBER_MAX_LENGTH),
        )
        object.__setattr__(
            self,
            "description",
            _optional_text(self.description, "description", DESCRIPTION_MAX_LENGTH),
        )
        object.__setattr__(self, "created_at", _utc_datetime(self.created_at, "created_at"))
        object.__setattr__(self, "updated_at", _utc_datetime(self.updated_at, "updated_at"))
        if isinstance(self.source_count, bool) or not isinstance(self.source_count, int):
            raise ValueError("source_count must be an integer")
        if self.source_count < 0:
            raise ValueError("source_count must be non-negative")
        if isinstance(self.version, bool) or not isinstance(self.version, int):
            raise ValueError("version must be an integer")
        if self.version < 1:
            raise ValueError("version must be positive")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot precede created_at")

    @classmethod
    def create(
        cls,
        *,
        name: str,
        manufacturer: str | None = None,
        model_number: str | None = None,
        category: ProductCategory = ProductCategory.UNCLASSIFIED,
        description: str | None = None,
        now: datetime | None = None,
    ) -> Self:
        timestamp = _utc_datetime(now or datetime.now(UTC), "now")
        return cls(
            product_id=uuid4(),
            name=name,
            manufacturer=manufacturer,
            model_number=model_number,
            category=category,
            status=ProductStatus.DRAFT,
            description=description,
            source_count=0,
            created_at=timestamp,
            updated_at=timestamp,
            version=1,
        )


@dataclass(frozen=True, slots=True)
class ProductPage:
    items: tuple[Product, ...]
    next_cursor: str | None
