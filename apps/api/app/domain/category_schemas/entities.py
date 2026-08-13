"""Immutable canonical category-attribute-schema domain models."""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Self

from app.core.exceptions import (
    CategoryAttributeAliasConflictError,
    CategoryAttributeSchemaValidationError,
)
from app.domain.category_schemas.enums import AttributeDataType, CategoryAttributeSchemaStatus
from app.domain.category_schemas.validation import (
    CANONICAL_NAME_PATTERN,
    MAX_ALIAS_LENGTH,
    MAX_ALIASES_PER_ATTRIBUTE,
    MAX_ATTRIBUTES,
    MAX_EXAMPLE_LENGTH,
    MAX_EXAMPLES_PER_ATTRIBUTE,
    bounded_text,
    normalize_alias,
)
from app.domain.products import ProductCategory

SUPPORTED_SCHEMA_CATEGORIES = frozenset(
    {ProductCategory.CENTRIFUGAL_PUMP, ProductCategory.INDUCTION_MOTOR}
)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnitDefinition:
    symbol: str
    canonical: str
    dimension: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", bounded_text(self.symbol, "unit symbol", 30))
        object.__setattr__(self, "canonical", bounded_text(self.canonical, "canonical unit", 30))
        if self.dimension is not None:
            object.__setattr__(
                self, "dimension", bounded_text(self.dimension, "unit dimension", 50)
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class AttributeValidationRules:
    min_value: int | Decimal | None = None
    max_value: int | Decimal | None = None
    allowed_values: tuple[str, ...] = ()
    pattern: str | None = None

    def __post_init__(self) -> None:
        for field, value in (("min_value", self.min_value), ("max_value", self.max_value)):
            if isinstance(value, (bool, float)) or (
                value is not None and not isinstance(value, (int, Decimal))
            ):
                raise CategoryAttributeSchemaValidationError(
                    f"{field} must be an integer or Decimal"
                )
        if (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            raise CategoryAttributeSchemaValidationError("min_value cannot exceed max_value")
        values = tuple(bounded_text(value, "allowed value", 100) for value in self.allowed_values)
        if len(values) != len(set(values)) or len(values) > 100:
            raise CategoryAttributeSchemaValidationError(
                "allowed values must be unique and contain at most 100 entries"
            )
        pattern = (
            bounded_text(self.pattern, "validation pattern", 200)
            if self.pattern is not None
            else None
        )
        object.__setattr__(self, "allowed_values", values)
        object.__setattr__(self, "pattern", pattern)


@dataclass(frozen=True, slots=True, kw_only=True)
class AttributeDefinition:
    attribute_id: str
    canonical_name: str
    display_name: str
    description: str
    data_type: AttributeDataType
    required: bool
    allowed_units: tuple[UnitDefinition, ...] = ()
    aliases: tuple[str, ...] = ()
    example_values: tuple[str, ...] = ()
    validation_rules: AttributeValidationRules = AttributeValidationRules()
    display_order: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.canonical_name, str) or not CANONICAL_NAME_PATTERN.fullmatch(
            self.canonical_name
        ):
            raise CategoryAttributeSchemaValidationError(
                "canonical_name must be a safe camelCase identifier"
            )
        if self.attribute_id != self.canonical_name:
            raise CategoryAttributeSchemaValidationError("attribute_id must equal canonical_name")
        display_name = bounded_text(self.display_name, "display_name", 100)
        description = bounded_text(self.description, "description", 500)
        if not isinstance(self.data_type, AttributeDataType):
            raise CategoryAttributeSchemaValidationError("data_type is invalid")
        if not isinstance(self.required, bool):
            raise CategoryAttributeSchemaValidationError("required must be boolean")
        if (
            isinstance(self.display_order, bool)
            or not isinstance(self.display_order, int)
            or self.display_order < 1
        ):
            raise CategoryAttributeSchemaValidationError("display_order must be positive")
        if len(self.aliases) > MAX_ALIASES_PER_ATTRIBUTE:
            raise CategoryAttributeSchemaValidationError("attribute alias limit exceeded")
        aliases = tuple(bounded_text(alias, "alias", MAX_ALIAS_LENGTH) for alias in self.aliases)
        normalized_aliases = tuple(normalize_alias(alias) for alias in aliases)
        if len(normalized_aliases) != len(set(normalized_aliases)):
            raise CategoryAttributeSchemaValidationError(
                "aliases must be unique after normalization"
            )
        if len(self.example_values) > MAX_EXAMPLES_PER_ATTRIBUTE:
            raise CategoryAttributeSchemaValidationError("attribute example limit exceeded")
        examples = tuple(
            bounded_text(value, "example value", MAX_EXAMPLE_LENGTH)
            for value in self.example_values
        )
        if len(examples) != len(set(examples)):
            raise CategoryAttributeSchemaValidationError("example values must be unique")
        unit_symbols = tuple(unit.symbol for unit in self.allowed_units)
        if len(unit_symbols) != len(set(unit_symbols)):
            raise CategoryAttributeSchemaValidationError("allowed unit symbols must be unique")
        if self.allowed_units and self.data_type not in {
            AttributeDataType.NUMBER,
            AttributeDataType.INTEGER,
        }:
            raise CategoryAttributeSchemaValidationError(
                "units are allowed only for NUMBER or INTEGER attributes"
            )
        rules = self.validation_rules
        if not isinstance(rules, AttributeValidationRules):
            raise CategoryAttributeSchemaValidationError("validation_rules is invalid")
        if rules.allowed_values and self.data_type is AttributeDataType.NUMBER:
            raise CategoryAttributeSchemaValidationError(
                "NUMBER attributes cannot define allowed_values"
            )
        if (rules.min_value is not None or rules.max_value is not None) and self.data_type not in {
            AttributeDataType.NUMBER,
            AttributeDataType.INTEGER,
        }:
            raise CategoryAttributeSchemaValidationError(
                "numeric bounds require NUMBER or INTEGER data type"
            )
        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "aliases", aliases)
        object.__setattr__(self, "example_values", examples)


def _number(value: int | Decimal | None) -> str | None:
    return str(value) if value is not None else None


def calculate_schema_fingerprint(
    *,
    category: ProductCategory,
    version: int,
    status: CategoryAttributeSchemaStatus,
    description: str,
    attributes: tuple[AttributeDefinition, ...],
) -> str:
    canonical_attributes: list[dict[str, object]] = []
    for attribute in sorted(attributes, key=lambda value: value.canonical_name):
        canonical_attributes.append(
            {
                "attributeId": attribute.attribute_id,
                "canonicalName": attribute.canonical_name,
                "displayName": attribute.display_name,
                "description": attribute.description,
                "dataType": attribute.data_type.value,
                "required": attribute.required,
                "allowedUnits": [
                    {
                        "symbol": unit.symbol,
                        "canonical": unit.canonical,
                        "dimension": unit.dimension,
                    }
                    for unit in sorted(attribute.allowed_units, key=lambda value: value.symbol)
                ],
                "aliases": sorted(attribute.aliases, key=normalize_alias),
                "exampleValues": sorted(attribute.example_values),
                "validationRules": {
                    "minValue": _number(attribute.validation_rules.min_value),
                    "maxValue": _number(attribute.validation_rules.max_value),
                    "allowedValues": sorted(attribute.validation_rules.allowed_values),
                    "pattern": attribute.validation_rules.pattern,
                },
                "displayOrder": attribute.display_order,
            }
        )
    payload = {
        "category": category.value,
        "version": version,
        "status": status.value,
        "description": description,
        "attributes": canonical_attributes,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True)
class CategoryAttributeSchema:
    schema_id: str
    category: ProductCategory
    version: int
    status: CategoryAttributeSchemaStatus
    description: str
    attributes: tuple[AttributeDefinition, ...]
    schema_fingerprint: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.category not in SUPPORTED_SCHEMA_CATEGORIES:
            raise CategoryAttributeSchemaValidationError("category has no attribute schema")
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise CategoryAttributeSchemaValidationError("version must be a positive integer")
        if self.schema_id != f"{self.category.value}:{self.version}":
            raise CategoryAttributeSchemaValidationError("schema_id must be category:version")
        if not isinstance(self.status, CategoryAttributeSchemaStatus):
            raise CategoryAttributeSchemaValidationError("status is invalid")
        description = bounded_text(self.description, "schema description", 500)
        if not self.attributes or len(self.attributes) > MAX_ATTRIBUTES:
            raise CategoryAttributeSchemaValidationError(
                f"schema must contain between 1 and {MAX_ATTRIBUTES} attributes"
            )
        names = tuple(attribute.canonical_name for attribute in self.attributes)
        if len(names) != len(set(names)):
            raise CategoryAttributeSchemaValidationError("canonical names must be unique")
        orders = tuple(attribute.display_order for attribute in self.attributes)
        if len(orders) != len(set(orders)):
            raise CategoryAttributeSchemaValidationError("display orders must be unique")
        if not any(attribute.required for attribute in self.attributes):
            raise CategoryAttributeSchemaValidationError(
                "schema must contain at least one required attribute"
            )
        alias_map: dict[str, str] = {}
        for attribute in self.attributes:
            for alias in (attribute.canonical_name, attribute.display_name, *attribute.aliases):
                normalized = normalize_alias(alias)
                owner = alias_map.get(normalized)
                if owner is not None and owner != attribute.canonical_name:
                    raise CategoryAttributeAliasConflictError(
                        f"alias {normalized!r} conflicts between {owner} and "
                        f"{attribute.canonical_name}"
                    )
                alias_map[normalized] = attribute.canonical_name
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise CategoryAttributeSchemaValidationError("created_at must be timezone-aware")
        if self.updated_at.tzinfo is None or self.updated_at.utcoffset() is None:
            raise CategoryAttributeSchemaValidationError("updated_at must be timezone-aware")
        created = self.created_at.astimezone(UTC)
        updated = self.updated_at.astimezone(UTC)
        if updated < created:
            raise CategoryAttributeSchemaValidationError("updated_at cannot precede created_at")
        expected = calculate_schema_fingerprint(
            category=self.category,
            version=self.version,
            status=self.status,
            description=description,
            attributes=self.attributes,
        )
        if self.schema_fingerprint != expected:
            raise CategoryAttributeSchemaValidationError(
                "schema_fingerprint does not match content"
            )
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "created_at", created)
        object.__setattr__(self, "updated_at", updated)

    @classmethod
    def create(
        cls,
        *,
        category: ProductCategory,
        version: int,
        status: CategoryAttributeSchemaStatus,
        description: str,
        attributes: tuple[AttributeDefinition, ...],
        now: datetime | None = None,
    ) -> Self:
        timestamp = (now or datetime.now(UTC)).astimezone(UTC)
        normalized_description = bounded_text(description, "schema description", 500)
        return cls(
            schema_id=f"{category.value}:{version}",
            category=category,
            version=version,
            status=status,
            description=normalized_description,
            attributes=attributes,
            schema_fingerprint=calculate_schema_fingerprint(
                category=category,
                version=version,
                status=status,
                description=normalized_description,
                attributes=attributes,
            ),
            created_at=timestamp,
            updated_at=timestamp,
        )

    def resolve_alias(self, alias: str) -> AttributeDefinition | None:
        normalized = normalize_alias(alias)
        for attribute in self.attributes:
            candidates = (attribute.canonical_name, attribute.display_name, *attribute.aliases)
            if normalized in {normalize_alias(candidate) for candidate in candidates}:
                return attribute
        return None
