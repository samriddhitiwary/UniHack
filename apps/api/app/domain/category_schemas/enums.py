"""Category-attribute-schema enumerations."""

from enum import StrEnum


class AttributeDataType(StrEnum):
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    INTEGER = "INTEGER"
    BOOLEAN = "BOOLEAN"
    ENUM = "ENUM"


class CategoryAttributeSchemaStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
