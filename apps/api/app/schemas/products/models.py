"""Pydantic schemas for product construction and persistence boundaries."""

from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.domain.products.entities import (
    DESCRIPTION_MAX_LENGTH,
    MANUFACTURER_MAX_LENGTH,
    MODEL_NUMBER_MAX_LENGTH,
    NAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
)
from app.domain.products.enums import ProductCategory, ProductStatus

Name = Annotated[str, Field(min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)]


class ProductSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator(
        "manufacturer", "model_number", "description", mode="before", check_fields=False
    )
    @classmethod
    def blank_optional_text_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class ProductCreate(ProductSchema):
    name: Name
    manufacturer: str | None = Field(default=None, max_length=MANUFACTURER_MAX_LENGTH)
    model_number: str | None = Field(default=None, max_length=MODEL_NUMBER_MAX_LENGTH)
    category: ProductCategory = ProductCategory.UNCLASSIFIED
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)


class ProductUpdate(ProductSchema):
    name: Name | None = None
    manufacturer: str | None = Field(default=None, max_length=MANUFACTURER_MAX_LENGTH)
    model_number: str | None = Field(default=None, max_length=MODEL_NUMBER_MAX_LENGTH)
    category: ProductCategory | None = None
    status: ProductStatus | None = None
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)


class ProductRecord(ProductSchema):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    product_id: UUID
    name: Name
    manufacturer: str | None = Field(max_length=MANUFACTURER_MAX_LENGTH)
    model_number: str | None = Field(max_length=MODEL_NUMBER_MAX_LENGTH)
    category: ProductCategory
    status: ProductStatus
    description: str | None = Field(max_length=DESCRIPTION_MAX_LENGTH)
    source_count: int = Field(ge=0)
    created_at: AwareDatetime
    updated_at: AwareDatetime
    version: int = Field(ge=1)


class ProductListResult(ProductSchema):
    items: list[ProductRecord]
    next_cursor: str | None = None
