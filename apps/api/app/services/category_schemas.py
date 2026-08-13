"""Internal category-schema lookup, alias resolution, and built-in bootstrap."""

import logging

from app.core.exceptions import (
    CategoryAttributeSchemaNotAvailableError,
    CategoryAttributeSchemaValidationError,
    CategoryAttributeSchemaVersionDriftError,
)
from app.domain.category_schemas import (
    SUPPORTED_SCHEMA_CATEGORIES,
    AttributeDefinition,
    CategoryAttributeSchema,
)
from app.domain.category_schemas.builtins import built_in_category_schemas
from app.domain.products import ProductCategory
from app.repositories.category_schemas import CategoryAttributeSchemaRepository

logger = logging.getLogger(__name__)


class CategoryAttributeSchemaService:
    def __init__(
        self,
        repository: CategoryAttributeSchemaRepository,
        *,
        max_attributes: int = 100,
        max_aliases_per_attribute: int = 30,
    ) -> None:
        if min(max_attributes, max_aliases_per_attribute) < 1:
            raise ValueError("category schema limits must be positive")
        self._repository = repository
        self._max_attributes = max_attributes
        self._max_aliases = max_aliases_per_attribute

    def get_active_schema(self, *, category: ProductCategory) -> CategoryAttributeSchema:
        self._require_supported(category)
        schema = self._repository.get_active_by_category(category)
        if schema is None:
            raise CategoryAttributeSchemaNotAvailableError()
        self._validate_configured_limits(schema)
        return schema

    def get_schema(self, *, category: ProductCategory, version: int) -> CategoryAttributeSchema:
        self._require_supported(category)
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise CategoryAttributeSchemaNotAvailableError()
        schema = self._repository.get_by_category_and_version(category, version)
        if schema is None:
            raise CategoryAttributeSchemaNotAvailableError()
        self._validate_configured_limits(schema)
        return schema

    def resolve_alias(
        self,
        *,
        category: ProductCategory,
        alias: str,
        version: int | None = None,
    ) -> AttributeDefinition | None:
        schema = (
            self.get_active_schema(category=category)
            if version is None
            else self.get_schema(category=category, version=version)
        )
        return schema.resolve_alias(alias)

    def seed_builtins(self) -> tuple[CategoryAttributeSchema, ...]:
        candidates: list[tuple[CategoryAttributeSchema, CategoryAttributeSchema | None]] = []
        for desired in built_in_category_schemas():
            self._validate_configured_limits(desired)
            existing = self._repository.get_by_category_and_version(
                desired.category, desired.version
            )
            if existing is not None and existing.schema_fingerprint != desired.schema_fingerprint:
                logger.error(
                    "event=category_schema.version_drift category=%s version=%s "
                    "schema_id=%s expected_fingerprint=%s actual_fingerprint=%s",
                    desired.category.value,
                    desired.version,
                    desired.schema_id,
                    desired.schema_fingerprint,
                    existing.schema_fingerprint,
                )
                raise CategoryAttributeSchemaVersionDriftError()
            active = self._repository.get_active_by_category(desired.category)
            if active is not None and (
                active.version != desired.version
                or active.schema_fingerprint != desired.schema_fingerprint
            ):
                raise CategoryAttributeSchemaVersionDriftError()
            candidates.append((desired, existing))

        seeded: list[CategoryAttributeSchema] = []
        for desired, existing in candidates:
            if existing is not None:
                logger.info(
                    "event=category_schema.seed_skipped category=%s version=%s schema_id=%s "
                    "fingerprint=%s",
                    desired.category.value,
                    desired.version,
                    desired.schema_id,
                    desired.schema_fingerprint,
                )
                continue
            stored = self._repository.create(desired)
            seeded.append(stored)
            logger.info(
                "event=category_schema.seeded category=%s version=%s schema_id=%s "
                "attribute_count=%s fingerprint=%s",
                stored.category.value,
                stored.version,
                stored.schema_id,
                len(stored.attributes),
                stored.schema_fingerprint,
            )
        return tuple(seeded)

    @staticmethod
    def _require_supported(category: ProductCategory) -> None:
        if category not in SUPPORTED_SCHEMA_CATEGORIES:
            raise CategoryAttributeSchemaNotAvailableError()

    def _validate_configured_limits(self, schema: CategoryAttributeSchema) -> None:
        if len(schema.attributes) > self._max_attributes or any(
            len(attribute.aliases) > self._max_aliases for attribute in schema.attributes
        ):
            raise CategoryAttributeSchemaValidationError(
                "schema exceeds configured attribute or alias limits"
            )
