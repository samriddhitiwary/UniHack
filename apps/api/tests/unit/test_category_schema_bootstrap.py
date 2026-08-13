"""Built-in schema bootstrap and service tests."""

from dataclasses import replace

import pytest

from app.core.exceptions import (
    CategoryAttributeSchemaNotAvailableError,
    CategoryAttributeSchemaValidationError,
    CategoryAttributeSchemaVersionDriftError,
)
from app.domain.category_schemas import CategoryAttributeSchema
from app.domain.category_schemas.builtins import (
    centrifugal_pump_schema_v1,
    induction_motor_schema_v1,
)
from app.domain.products import ProductCategory
from app.services.category_schemas import CategoryAttributeSchemaService


class MemoryRepository:
    def __init__(self, schemas=()) -> None:
        self.schemas = {(schema.category, schema.version): schema for schema in schemas}
        self.created = []

    def create(self, schema):
        self.created.append(schema)
        self.schemas[(schema.category, schema.version)] = schema
        return schema

    def get_by_category_and_version(self, category, version):
        return self.schemas.get((category, version))

    def get_active_by_category(self, category):
        return next(
            (
                schema
                for (stored_category, _), schema in self.schemas.items()
                if stored_category is category and schema.status.value == "ACTIVE"
            ),
            None,
        )


def test_empty_repository_seeds_both_builtins_and_rerun_is_idempotent() -> None:
    repository = MemoryRepository()
    service = CategoryAttributeSchemaService(repository)
    seeded = service.seed_builtins()
    assert {schema.category for schema in seeded} == {
        ProductCategory.CENTRIFUGAL_PUMP,
        ProductCategory.INDUCTION_MOTOR,
    }
    assert service.seed_builtins() == ()
    assert len(repository.created) == 2


def test_identical_existing_schema_is_skipped_without_overwrite() -> None:
    existing = induction_motor_schema_v1()
    repository = MemoryRepository((existing,))
    seeded = CategoryAttributeSchemaService(repository).seed_builtins()
    assert seeded == (centrifugal_pump_schema_v1(),)
    assert repository.schemas[(existing.category, 1)] is existing


def test_different_persisted_fingerprint_raises_version_drift() -> None:
    built_in = induction_motor_schema_v1()
    changed_attribute = replace(
        built_in.attributes[0], aliases=(*built_in.attributes[0].aliases, "changed alias")
    )
    changed = CategoryAttributeSchema.create(
        category=built_in.category,
        version=1,
        status=built_in.status,
        description=built_in.description,
        attributes=(changed_attribute, *built_in.attributes[1:]),
        now=built_in.created_at,
    )
    repository = MemoryRepository((changed,))
    with pytest.raises(CategoryAttributeSchemaVersionDriftError):
        CategoryAttributeSchemaService(repository).seed_builtins()
    assert repository.created == []


def test_service_get_version_active_unknown_and_configured_limits() -> None:
    motor = induction_motor_schema_v1()
    repository = MemoryRepository((motor,))
    service = CategoryAttributeSchemaService(repository)
    assert service.get_schema(category=motor.category, version=1) is motor
    assert service.get_active_schema(category=motor.category) is motor
    with pytest.raises(CategoryAttributeSchemaNotAvailableError):
        service.get_schema(category=motor.category, version=2)
    with pytest.raises(CategoryAttributeSchemaNotAvailableError):
        service.resolve_alias(category=ProductCategory.UNCLASSIFIED, alias="rated power")
    with pytest.raises(CategoryAttributeSchemaValidationError):
        CategoryAttributeSchemaService(repository, max_attributes=1).get_active_schema(
            category=motor.category
        )
