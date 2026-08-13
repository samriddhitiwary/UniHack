"""Reusable category-schema test fixtures."""

from app.domain.category_schemas import (
    AttributeDataType,
    AttributeDefinition,
    AttributeValidationRules,
    CategoryAttributeSchema,
    CategoryAttributeSchemaStatus,
    UnitDefinition,
)
from app.domain.category_schemas.builtins import BUILTIN_SCHEMA_CREATED_AT
from app.domain.products import ProductCategory


def make_attribute(
    name: str = "ratedPower",
    *,
    order: int = 1,
    required: bool = True,
    aliases: tuple[str, ...] = ("rated power",),
    units: tuple[UnitDefinition, ...] = (UnitDefinition(symbol="kW", canonical="kW"),),
    data_type: AttributeDataType = AttributeDataType.NUMBER,
    rules: AttributeValidationRules | None = None,
) -> AttributeDefinition:
    return AttributeDefinition(
        attribute_id=name,
        canonical_name=name,
        display_name="Rated Power" if name == "ratedPower" else "Other Value",
        description="A bounded technical attribute used by tests.",
        data_type=data_type,
        required=required,
        allowed_units=units,
        aliases=aliases,
        example_values=("5.5 kW",),
        validation_rules=rules or AttributeValidationRules(min_value=0),
        display_order=order,
    )


def make_schema(
    *,
    attributes: tuple[AttributeDefinition, ...] | None = None,
    category: ProductCategory = ProductCategory.INDUCTION_MOTOR,
    version: int = 1,
    status: CategoryAttributeSchemaStatus = CategoryAttributeSchemaStatus.ACTIVE,
) -> CategoryAttributeSchema:
    return CategoryAttributeSchema.create(
        category=category,
        version=version,
        status=status,
        description="A bounded category schema used by tests.",
        attributes=attributes or (make_attribute(),),
        now=BUILTIN_SCHEMA_CREATED_AT,
    )
