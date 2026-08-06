"""Safe opaque cursor encoding for DynamoDB pagination keys."""

import base64
import binascii
import json
from typing import Any

from app.core.exceptions import InvalidProductCursorError


def encode_product_cursor(key: dict[str, Any] | None) -> str | None:
    if not key:
        return None
    try:
        payload = json.dumps(key, separators=(",", ":"), sort_keys=True).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidProductCursorError("pagination key cannot be encoded") from exc
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_product_cursor(cursor: str | None) -> dict[str, Any] | None:
    if cursor is None:
        return None
    if not cursor or len(cursor) > 4_096:
        raise InvalidProductCursorError("product cursor is malformed")
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.b64decode(cursor + padding, altchars=b"-_", validate=True)
        decoded = json.loads(raw.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidProductCursorError("product cursor is malformed") from exc
    if not isinstance(decoded, dict) or not decoded:
        raise InvalidProductCursorError("product cursor must contain a pagination key")
    if not all(isinstance(key, str) and isinstance(value, dict) for key, value in decoded.items()):
        raise InvalidProductCursorError("product cursor has an invalid structure")
    return decoded
