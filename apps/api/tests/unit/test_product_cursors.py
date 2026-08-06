"""Opaque cursor tests."""

import pytest

from app.core.exceptions import InvalidProductCursorError
from app.utils.cursors import decode_product_cursor, encode_product_cursor


def test_cursor_round_trip_and_missing_cursor() -> None:
    key = {
        "productId": {"S": "one"},
        "entityType": {"S": "PRODUCT"},
        "createdAt": {"S": "2026-08-06T11:30:00.000000Z"},
    }
    cursor = encode_product_cursor(key)
    assert cursor is not None
    assert "{" not in cursor
    assert decode_product_cursor(cursor) == key
    assert encode_product_cursor(None) is None
    assert decode_product_cursor(None) is None


@pytest.mark.parametrize("cursor", ["", "not-base64!", "e30", "W10"])
def test_malformed_cursor_is_rejected(cursor: str) -> None:
    with pytest.raises(InvalidProductCursorError):
        decode_product_cursor(cursor)
