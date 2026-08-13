"""Category-schema DynamoDB serialization tests."""

import pytest

from app.core.exceptions import CategoryAttributeSchemaSerializationError, ProductSerializationError
from app.domain.products import ProductCategory
from app.schemas.category_schemas import CategoryAttributeSchemaRecord
from app.utils.dynamodb import (
    category_attribute_schema_from_item,
    category_attribute_schema_to_item,
    deserialize_item,
    serialize_item,
)
from tests.fixtures.category_schemas import make_schema


def test_full_schema_round_trip_preserves_nested_metadata_and_fingerprint() -> None:
    schema = make_schema()
    item = category_attribute_schema_to_item(schema)
    restored = category_attribute_schema_from_item(deserialize_item(serialize_item(item)))
    assert restored == schema
    assert item["category"] is ProductCategory.INDUCTION_MOTOR
    assert item["version"] == 1
    record = CategoryAttributeSchemaRecord.model_validate(schema)
    assert record.model_dump(by_alias=True)["schemaFingerprint"] == schema.schema_fingerprint


@pytest.mark.parametrize(
    "mutation",
    (
        lambda item: item.pop("schemaId"),
        lambda item: item.__setitem__("category", "UNCLASSIFIED"),
        lambda item: item.__setitem__("schemaFingerprint", "0" * 64),
        lambda item: item["attributes"].append(item["attributes"][0]),
    ),
)
def test_malformed_schema_items_are_controlled(mutation) -> None:
    item = deserialize_item(serialize_item(category_attribute_schema_to_item(make_schema())))
    mutation(item)
    with pytest.raises(CategoryAttributeSchemaSerializationError):
        category_attribute_schema_from_item(item)


def test_float_persistence_is_rejected() -> None:
    item = category_attribute_schema_to_item(make_schema())
    item["attributes"][0]["validationRules"]["minValue"] = 1.5
    with pytest.raises(ProductSerializationError):
        serialize_item(item)
