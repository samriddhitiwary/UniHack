"""Canonical category-attribute-schema domain."""

from app.domain.category_schemas.entities import (
    SUPPORTED_SCHEMA_CATEGORIES,
    AttributeDefinition,
    AttributeValidationRules,
    CategoryAttributeSchema,
    UnitDefinition,
    calculate_schema_fingerprint,
)
from app.domain.category_schemas.enums import AttributeDataType, CategoryAttributeSchemaStatus
from app.domain.category_schemas.validation import normalize_alias

__all__ = [
    "SUPPORTED_SCHEMA_CATEGORIES",
    "AttributeDataType",
    "AttributeDefinition",
    "AttributeValidationRules",
    "CategoryAttributeSchema",
    "CategoryAttributeSchemaStatus",
    "UnitDefinition",
    "calculate_schema_fingerprint",
    "normalize_alias",
]
