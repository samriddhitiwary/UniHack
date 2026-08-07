"""Safe opaque cursor encoding for DynamoDB pagination keys."""

import base64
import binascii
import json
from typing import Any
from uuid import UUID

from app.core.exceptions import (
    InvalidProcessingJobCursorError,
    InvalidProductCursorError,
    InvalidProductSourceCursorError,
)

PRODUCT_SOURCE_CURSOR_SCOPE = "product_sources"
PROCESSING_JOBS_BY_PRODUCT_SCOPE = "processing_jobs_by_product"
PROCESSING_JOBS_BY_SOURCE_SCOPE = "processing_jobs_by_source"


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


def encode_product_source_cursor(product_id: UUID, key: dict[str, Any] | None) -> str | None:
    if not key:
        return None
    envelope = {
        "scope": PRODUCT_SOURCE_CURSOR_SCOPE,
        "productId": str(product_id),
        "key": key,
    }
    try:
        payload = json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidProductSourceCursorError("source pagination key cannot be encoded") from exc
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_product_source_cursor(cursor: str | None, product_id: UUID) -> dict[str, Any] | None:
    if cursor is None:
        return None
    if not cursor or len(cursor) > 4_096:
        raise InvalidProductSourceCursorError("product-source cursor is malformed")
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.b64decode(cursor + padding, altchars=b"-_", validate=True)
        decoded = json.loads(raw.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidProductSourceCursorError("product-source cursor is malformed") from exc
    if not isinstance(decoded, dict) or set(decoded) != {"scope", "productId", "key"}:
        raise InvalidProductSourceCursorError("product-source cursor has an invalid structure")
    if decoded["scope"] != PRODUCT_SOURCE_CURSOR_SCOPE:
        raise InvalidProductSourceCursorError("product-source cursor has an invalid scope")
    if decoded["productId"] != str(product_id):
        raise InvalidProductSourceCursorError("product-source cursor belongs to another product")
    key = decoded["key"]
    if not isinstance(key, dict) or not key:
        raise InvalidProductSourceCursorError("product-source cursor has no pagination key")
    if not all(isinstance(name, str) and isinstance(value, dict) for name, value in key.items()):
        raise InvalidProductSourceCursorError("product-source cursor key is invalid")
    return key


def encode_processing_job_product_cursor(
    product_id: UUID, key: dict[str, Any] | None
) -> str | None:
    return _encode_processing_job_cursor(
        PROCESSING_JOBS_BY_PRODUCT_SCOPE,
        {"productId": str(product_id)},
        key,
    )


def decode_processing_job_product_cursor(
    cursor: str | None, product_id: UUID
) -> dict[str, Any] | None:
    return _decode_processing_job_cursor(
        cursor,
        PROCESSING_JOBS_BY_PRODUCT_SCOPE,
        {"productId": str(product_id)},
    )


def encode_processing_job_source_cursor(
    product_id: UUID, source_id: UUID, key: dict[str, Any] | None
) -> str | None:
    return _encode_processing_job_cursor(
        PROCESSING_JOBS_BY_SOURCE_SCOPE,
        {"productId": str(product_id), "sourceId": str(source_id)},
        key,
    )


def decode_processing_job_source_cursor(
    cursor: str | None, product_id: UUID, source_id: UUID
) -> dict[str, Any] | None:
    return _decode_processing_job_cursor(
        cursor,
        PROCESSING_JOBS_BY_SOURCE_SCOPE,
        {"productId": str(product_id), "sourceId": str(source_id)},
    )


def _encode_processing_job_cursor(
    scope: str,
    identity: dict[str, str],
    key: dict[str, Any] | None,
) -> str | None:
    if not key:
        return None
    try:
        payload = json.dumps(
            {"scope": scope, "identity": identity, "key": key},
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidProcessingJobCursorError("job pagination key cannot be encoded") from exc
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_processing_job_cursor(
    cursor: str | None,
    scope: str,
    identity: dict[str, str],
) -> dict[str, Any] | None:
    if cursor is None:
        return None
    if not cursor or len(cursor) > 4_096:
        raise InvalidProcessingJobCursorError("processing-job cursor is malformed")
    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.b64decode(cursor + padding, altchars=b"-_", validate=True)
        decoded = json.loads(raw.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidProcessingJobCursorError("processing-job cursor is malformed") from exc
    if not isinstance(decoded, dict) or set(decoded) != {"scope", "identity", "key"}:
        raise InvalidProcessingJobCursorError("processing-job cursor has an invalid structure")
    if decoded["scope"] != scope or decoded["identity"] != identity:
        raise InvalidProcessingJobCursorError("processing-job cursor scope is invalid")
    key = decoded["key"]
    if not isinstance(key, dict) or not key:
        raise InvalidProcessingJobCursorError("processing-job cursor has no pagination key")
    if not all(isinstance(name, str) and isinstance(value, dict) for name, value in key.items()):
        raise InvalidProcessingJobCursorError("processing-job cursor key is invalid")
    return key
