"""Scoped product-source cursor tests."""

from uuid import uuid4

import pytest

from app.core.exceptions import InvalidProductSourceCursorError
from app.utils.cursors import (
    decode_product_source_cursor,
    encode_product_cursor,
    encode_product_source_cursor,
)
from app.utils.dynamodb import serialize_item
from tests.fixtures.product_sources import SOURCE_CREATED_AT, SOURCE_ID
from tests.fixtures.products import PRODUCT_ID


def test_source_cursor_round_trip_is_scoped_to_product() -> None:
    key = serialize_item(
        {"productId": PRODUCT_ID, "sourceId": SOURCE_ID, "createdAt": SOURCE_CREATED_AT}
    )
    cursor = encode_product_source_cursor(PRODUCT_ID, key)
    assert cursor is not None
    assert decode_product_source_cursor(cursor, PRODUCT_ID) == key
    assert str(PRODUCT_ID) not in cursor


def test_empty_source_key_has_no_cursor() -> None:
    assert encode_product_source_cursor(PRODUCT_ID, None) is None
    assert decode_product_source_cursor(None, PRODUCT_ID) is None


def test_source_cursor_rejects_another_product_and_product_cursor() -> None:
    key = serialize_item(
        {"productId": PRODUCT_ID, "sourceId": SOURCE_ID, "createdAt": SOURCE_CREATED_AT}
    )
    cursor = encode_product_source_cursor(PRODUCT_ID, key)
    with pytest.raises(InvalidProductSourceCursorError):
        decode_product_source_cursor(cursor, uuid4())
    product_cursor = encode_product_cursor(serialize_item({"productId": PRODUCT_ID}))
    with pytest.raises(InvalidProductSourceCursorError):
        decode_product_source_cursor(product_cursor, PRODUCT_ID)


@pytest.mark.parametrize("cursor", ["", "not-base64", "e30", "W10"])
def test_source_cursor_rejects_malformed_values(cursor: str) -> None:
    with pytest.raises(InvalidProductSourceCursorError):
        decode_product_source_cursor(cursor, PRODUCT_ID)
