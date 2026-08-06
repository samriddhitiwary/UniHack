"""Pydantic schemas for product construction and persistence boundaries."""

from typing import Annotated, ClassVar, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.json_schema import SkipJsonSchema

from app.domain.products.entities import (
    DESCRIPTION_MAX_LENGTH,
    MANUFACTURER_MAX_LENGTH,
    MODEL_NUMBER_MAX_LENGTH,
    NAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
)
from app.domain.products.enums import ProductCategory, ProductStatus

Name = Annotated[str, Field(min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)]


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(word.capitalize() for word in rest)


class ProductSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
        str_strip_whitespace=True,
    )

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
    editable_fields: ClassVar[frozenset[str]] = frozenset(
        {"name", "manufacturer", "model_number", "category", "status", "description"}
    )
    non_nullable_fields: ClassVar[frozenset[str]] = frozenset({"name", "category", "status"})

    version: int = Field(ge=1, strict=True)
    name: Name | SkipJsonSchema[None] = None
    manufacturer: str | None = Field(default=None, max_length=MANUFACTURER_MAX_LENGTH)
    model_number: str | None = Field(default=None, max_length=MODEL_NUMBER_MAX_LENGTH)
    category: ProductCategory | SkipJsonSchema[None] = None
    status: ProductStatus | SkipJsonSchema[None] = None
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)

    @model_validator(mode="after")
    def validate_supplied_fields(self) -> Self:
        supplied_updates = self.model_fields_set & self.editable_fields
        if not supplied_updates:
            raise ValueError("at least one editable product field is required")
        if any(
            getattr(self, field) is None for field in supplied_updates & self.non_nullable_fields
        ):
            raise ValueError("name, category, and status cannot be null")
        return self


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
