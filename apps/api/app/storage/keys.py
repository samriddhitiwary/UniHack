"""Platform-independent object-key generation and validation."""

import re
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from app.core.exceptions import InvalidObjectKeyError, UnsupportedObjectExtensionError

OBJECT_KEY_MAX_LENGTH = 1_024
OBJECT_KEY_SEGMENT_MAX_LENGTH = 255
METADATA_SUFFIX = ".metadata.json"
ALLOWED_OBJECT_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".webp", ".csv"})

_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")
_URL_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")


def generate_object_key(*, product_id: UUID, source_id: UUID, original_filename: str) -> str:
    """Generate an opaque stored filename under product/source UUID namespaces."""
    if not isinstance(product_id, UUID) or not isinstance(source_id, UUID):
        raise InvalidObjectKeyError("product_id and source_id must be UUIDs")
    filename = original_filename.strip()
    if not filename or "\x00" in filename or "/" in filename or "\\" in filename:
        raise UnsupportedObjectExtensionError("original filename must have an approved extension")
    extension = PurePosixPath(filename).suffix.lower()
    if extension not in ALLOWED_OBJECT_EXTENSIONS:
        raise UnsupportedObjectExtensionError("object extension is unsupported")
    key = f"products/{product_id}/sources/{source_id}/{uuid4()}{extension}"
    validate_object_key(key)
    return key


def validate_object_key(object_key: str) -> str:
    """Return a safe logical key or raise a controlled validation error."""
    if not isinstance(object_key, str):
        raise InvalidObjectKeyError("object key must be a string")
    if not object_key or not object_key.strip():
        raise InvalidObjectKeyError("object key must not be empty")
    if object_key != object_key.strip():
        raise InvalidObjectKeyError("object key must not have surrounding whitespace")
    if len(object_key) > OBJECT_KEY_MAX_LENGTH:
        raise InvalidObjectKeyError("object key is too long")
    if object_key.startswith(("/", "\\")) or _DRIVE_PREFIX.match(object_key):
        raise InvalidObjectKeyError("object key must be relative")
    if _URL_SCHEME.match(object_key) or "\\" in object_key or "\x00" in object_key:
        raise InvalidObjectKeyError("object key contains an unsafe path form")
    if any(ord(character) < 32 or ord(character) == 127 for character in object_key):
        raise InvalidObjectKeyError("object key contains control characters")

    segments = object_key.split("/")
    if any(
        not segment
        or segment in {".", ".."}
        or len(segment) > OBJECT_KEY_SEGMENT_MAX_LENGTH
        or not _SAFE_SEGMENT.fullmatch(segment)
        for segment in segments
    ):
        raise InvalidObjectKeyError("object key contains an unsafe path segment")
    final_segment = segments[-1]
    if final_segment.endswith(METADATA_SUFFIX) or ".tmp-" in final_segment:
        raise InvalidObjectKeyError("object key uses a reserved storage name")
    return object_key
