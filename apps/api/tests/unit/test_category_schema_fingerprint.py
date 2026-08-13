"""Deterministic schema-fingerprint tests."""

from dataclasses import replace
from datetime import timedelta

from app.domain.category_schemas import CategoryAttributeSchema, UnitDefinition
from tests.fixtures.category_schemas import make_attribute, make_schema


def rebuild(schema, attributes):
    return CategoryAttributeSchema.create(
        category=schema.category,
        version=schema.version,
        status=schema.status,
        description=schema.description,
        attributes=attributes,
        now=schema.created_at,
    )


def test_identical_content_and_reordered_attributes_have_same_fingerprint() -> None:
    first = make_attribute()
    second = make_attribute("otherValue", order=2, aliases=("other value",), units=())
    left = make_schema(attributes=(first, second))
    right = make_schema(attributes=(second, first))
    assert left.schema_fingerprint == right.schema_fingerprint


def test_alias_unit_and_required_changes_alter_fingerprint() -> None:
    schema = make_schema()
    attribute = schema.attributes[0]
    changes = (
        replace(attribute, aliases=(*attribute.aliases, "output power")),
        replace(
            attribute,
            allowed_units=(*attribute.allowed_units, UnitDefinition(symbol="W", canonical="W")),
        ),
        replace(attribute, required=False),
    )
    fingerprints = {rebuild(schema, (changed,)).schema_fingerprint for changed in changes[:2]}
    optional = changes[2]
    fallback = make_attribute("otherValue", order=2, aliases=(), units=())
    fingerprints.add(rebuild(schema, (optional, fallback)).schema_fingerprint)
    assert schema.schema_fingerprint not in fingerprints
    assert len(fingerprints) == 3


def test_timestamp_change_does_not_change_fingerprint() -> None:
    schema = make_schema()
    shifted = replace(
        schema,
        created_at=schema.created_at + timedelta(days=1),
        updated_at=schema.updated_at + timedelta(days=1),
    )
    assert shifted.schema_fingerprint == schema.schema_fingerprint
