"""Central DynamoDB serialization tests."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.exceptions import ProductSerializationError
from app.domain.products import ProductCategory
from app.schemas.products import ProductCreate
from app.utils.dynamodb import (
    deserialize_item,
    format_utc,
    product_from_item,
    product_to_item,
    serialize_item,
    to_dynamodb_compatible,
)
from tests.fixtures.products import PRODUCT_ID, make_product


def test_product_round_trip_preserves_uuid_enum_and_timestamp() -> None:
    product = make_product()
    native = product_to_item(product)
    wire = serialize_item(native)
    restored = product_from_item(deserialize_item(wire))

    assert native["productId"] == PRODUCT_ID
    assert wire["productId"] == {"S": str(PRODUCT_ID)}
    assert wire["category"] == {"S": "CENTRIFUGAL_PUMP"}
    assert wire["description"] == {"NULL": True}
    assert wire["createdAt"] == {"S": "2026-08-06T11:30:00.000000Z"}
    assert restored == product


def test_generic_conversion_supports_models_decimal_uuid_and_nested_values() -> None:
    identifier = uuid4()
    model = ProductCreate(name="Valid pump", category=ProductCategory.CENTRIFUGAL_PUMP)
    converted = to_dynamodb_compatible(
        {"model": model, "score": Decimal("1.25"), "ids": [identifier]}
    )
    assert converted["model"]["category"] == "CENTRIFUGAL_PUMP"
    assert converted["score"] == Decimal("1.25")
    assert converted["ids"] == [str(identifier)]


def test_serialization_rejects_python_float_at_any_depth() -> None:
    with pytest.raises(ProductSerializationError, match="floats"):
        serialize_item({"nested": {"unsafe": [1.5]}})


@pytest.mark.parametrize(
    "item",
    [
        {},
        {"entityType": "OTHER"},
        {
            **product_to_item(make_product()),
            "createdAt": "not-a-date",
        },
        {
            **product_to_item(make_product()),
            "sourceCount": Decimal("1.5"),
        },
    ],
)
def test_invalid_product_items_raise_controlled_error(item: dict[str, object]) -> None:
    with pytest.raises(ProductSerializationError):
        product_from_item(item)


def test_format_utc_rejects_naive_datetime() -> None:
    with pytest.raises(ProductSerializationError, match="timezone-aware"):
        format_utc(datetime(2026, 8, 6, 12, 0))
    assert format_utc(datetime(2026, 8, 6, 12, 0, tzinfo=UTC)).endswith(".000000Z")
