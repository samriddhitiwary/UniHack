"""Strict internal schemas for category-attribute-schema boundaries."""

from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.category_schemas import AttributeDataType, CategoryAttributeSchemaStatus
from app.domain.products import ProductCategory
from app.schemas.products.models import to_camel


class CategorySchemaModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class UnitDefinitionRecord(CategorySchemaModel):
    symbol: str = Field(min_length=1, max_length=30)
    canonical: str = Field(min_length=1, max_length=30)
    dimension: str | None = Field(default=None, min_length=1, max_length=50)


class AttributeValidationRulesRecord(CategorySchemaModel):
    min_value: int | Decimal | None = None
    max_value: int | Decimal | None = None
    allowed_values: tuple[str, ...] = ()
    pattern: str | None = Field(default=None, min_length=1, max_length=200)


class AttributeDefinitionRecord(CategorySchemaModel):
    attribute_id: str
    canonical_name: str
    display_name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)
    data_type: AttributeDataType
    required: bool
    allowed_units: tuple[UnitDefinitionRecord, ...] = ()
    aliases: tuple[str, ...] = ()
    example_values: tuple[str, ...] = ()
    validation_rules: AttributeValidationRulesRecord
    display_order: int = Field(gt=0)


class CategoryAttributeSchemaRecord(CategorySchemaModel):
    schema_id: str
    category: ProductCategory
    version: int = Field(gt=0)
    status: CategoryAttributeSchemaStatus
    description: str = Field(min_length=1, max_length=500)
    attributes: tuple[AttributeDefinitionRecord, ...]
    schema_fingerprint: str = Field(min_length=64, max_length=64)
    created_at: AwareDatetime
    updated_at: AwareDatetime
