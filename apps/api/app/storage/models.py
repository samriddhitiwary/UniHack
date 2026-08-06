"""Immutable metadata returned by object-storage implementations."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from app.storage.keys import validate_object_key

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True, kw_only=True)
class StoredObject:
    """Provider-independent metadata for one stored binary object."""

    object_key: str
    size_bytes: int
    checksum_sha256: str
    created_at: datetime

    def __post_init__(self) -> None:
        validate_object_key(self.object_key)
        if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int):
            raise ValueError("size_bytes must be an integer")
        if self.size_bytes < 0:
            raise ValueError("size_bytes must be non-negative")
        if not _SHA256_PATTERN.fullmatch(self.checksum_sha256):
            raise ValueError("checksum_sha256 must be 64 lowercase hexadecimal characters")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))
