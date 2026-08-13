"""Attribute-definition and category-schema invariant tests."""

from dataclasses import FrozenInstanceError, replace

import pytest

from app.core.exceptions import (
    CategoryAttributeAliasConflictError,
    CategoryAttributeSchemaValidationError,
)
from app.domain.category_schemas import (
    AttributeDataType,
    AttributeValidationRules,
    CategoryAttributeSchema,
    CategoryAttributeSchemaStatus,
    UnitDefinition,
    normalize_alias,
)
from app.domain.category_schemas.builtins import BUILTIN_SCHEMA_CREATED_AT
from app.domain.products import ProductCategory
from tests.fixtures.category_schemas import make_attribute, make_schema


def test_valid_models_are_immutable_and_identified_deterministically() -> None:
    attribute = make_attribute()
    schema = make_schema()
    assert attribute.attribute_id == attribute.canonical_name == "ratedPower"
    assert schema.schema_id == "INDUCTION_MOTOR:1"
    with pytest.raises(FrozenInstanceError):
        attribute.required = False  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        schema.version = 2  # type: ignore[misc]


@pytest.mark.parametrize("name", ("RatedPower", "rated_power", "1power", "rated power", ""))
def test_invalid_canonical_names_are_rejected(name: str) -> None:
    with pytest.raises(CategoryAttributeSchemaValidationError):
        make_attribute(name)


def test_attribute_id_display_description_and_order_are_validated() -> None:
    base = make_attribute()
    for changes in (
        {"attribute_id": "other"},
        {"display_name": " "},
        {"description": "x" * 501},
        {"display_order": 0},
    ):
        with pytest.raises(CategoryAttributeSchemaValidationError):
            replace(base, **changes)


def test_units_are_numeric_only_unique_and_nonblank() -> None:
    with pytest.raises(CategoryAttributeSchemaValidationError):
        make_attribute(data_type=AttributeDataType.TEXT)
    duplicate = UnitDefinition(symbol="kW", canonical="kW")
    with pytest.raises(CategoryAttributeSchemaValidationError):
        make_attribute(units=(duplicate, duplicate))
    with pytest.raises(CategoryAttributeSchemaValidationError):
        UnitDefinition(symbol=" ", canonical="kW")


def test_alias_normalization_and_duplicate_aliases() -> None:
    assert normalize_alias("  RATED_Power--Value ") == "rated power value"
    with pytest.raises(CategoryAttributeSchemaValidationError):
        make_attribute(aliases=("Rated-Power", "rated_power"))


def test_cross_attribute_alias_and_implicit_display_collisions_are_rejected() -> None:
    first = make_attribute(aliases=("shared value",))
    second = make_attribute("otherValue", order=2, aliases=("shared-value",), units=())
    with pytest.raises(CategoryAttributeAliasConflictError):
        make_schema(attributes=(first, second))


def test_schema_rejects_duplicate_names_orders_and_no_required_attribute() -> None:
    first = make_attribute()
    cases = (
        (first, replace(first, display_order=2)),
        (first, make_attribute("otherValue", order=1, units=())),
        (replace(first, required=False),),
    )
    for attributes in cases:
        with pytest.raises(CategoryAttributeSchemaValidationError):
            make_schema(attributes=attributes)


@pytest.mark.parametrize("version", (0, -1, True))
def test_schema_version_must_be_positive_integer(version: int) -> None:
    with pytest.raises(CategoryAttributeSchemaValidationError):
        make_schema(version=version)


def test_unclassified_schema_is_rejected() -> None:
    with pytest.raises(CategoryAttributeSchemaValidationError):
        make_schema(category=ProductCategory.UNCLASSIFIED)


def test_alias_example_and_attribute_limits_are_enforced() -> None:
    with pytest.raises(CategoryAttributeSchemaValidationError):
        make_attribute(aliases=tuple(f"alias {index}" for index in range(31)))
    with pytest.raises(CategoryAttributeSchemaValidationError):
        replace(make_attribute(), example_values=tuple(str(index) for index in range(11)))
    attributes = tuple(
        replace(
            make_attribute(f"value{index}", order=index + 1, aliases=(), units=()),
            display_name=f"Value {index}",
        )
        for index in range(101)
    )
    with pytest.raises(CategoryAttributeSchemaValidationError):
        make_schema(attributes=attributes)


def test_validation_rules_reject_incoherent_or_unsafe_metadata() -> None:
    with pytest.raises(CategoryAttributeSchemaValidationError):
        AttributeValidationRules(min_value=100, max_value=10)
    with pytest.raises(CategoryAttributeSchemaValidationError):
        AttributeValidationRules(min_value=1.5)
    with pytest.raises(CategoryAttributeSchemaValidationError):
        make_attribute(rules=AttributeValidationRules(allowed_values=("5",)))
    text = make_attribute(
        data_type=AttributeDataType.TEXT, units=(), rules=AttributeValidationRules()
    )
    with pytest.raises(CategoryAttributeSchemaValidationError):
        replace(text, validation_rules=AttributeValidationRules(min_value=0))


def test_alias_resolution_includes_canonical_and_display_names() -> None:
    schema = make_schema()
    assert schema.resolve_alias("ratedPower") is schema.attributes[0]
    assert schema.resolve_alias("RATED-POWER") is schema.attributes[0]
    assert schema.resolve_alias("unknown") is None


def test_fingerprint_and_timestamp_integrity_are_validated() -> None:
    schema = make_schema()
    with pytest.raises(CategoryAttributeSchemaValidationError):
        replace(schema, schema_fingerprint="0" * 64)
    with pytest.raises(CategoryAttributeSchemaValidationError):
        CategoryAttributeSchema(
            schema_id=schema.schema_id,
            category=schema.category,
            version=schema.version,
            status=CategoryAttributeSchemaStatus.ACTIVE,
            description=schema.description,
            attributes=schema.attributes,
            schema_fingerprint=schema.schema_fingerprint,
            created_at=BUILTIN_SCHEMA_CREATED_AT,
            updated_at=BUILTIN_SCHEMA_CREATED_AT.replace(year=2025),
        )
