"""Immutable product-source entities and metadata invariants."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from app.domain.product_sources.enums import ProductSourceStatus, ProductSourceType

ORIGINAL_FILENAME_MAX_LENGTH = 255
STORAGE_KEY_MAX_LENGTH = 1_024
MIME_TYPE_MAX_LENGTH = 255
DISPLAY_NAME_MAX_LENGTH = 200
TEXT_CONTENT_MAX_LENGTH = 50_000
ERROR_MESSAGE_MAX_LENGTH = 2_000

_CHECKSUM_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
_WINDOWS_ABSOLUTE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")
_ALLOWED_MIME_TYPES = {
    ProductSourceType.PDF: frozenset({"application/pdf"}),
    ProductSourceType.IMAGE: frozenset({"image/png", "image/jpeg", "image/webp"}),
    ProductSourceType.CSV: frozenset({"text/csv", "application/csv", "application/vnd.ms-excel"}),
    ProductSourceType.TEXT: frozenset({"text/plain"}),
}


def _optional_text(value: str | None, field: str, maximum: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > maximum:
        raise ValueError(f"{field} must contain at most {maximum} characters")
    return normalized


def _utc_datetime(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProductSource:
    source_id: UUID
    product_id: UUID
    source_type: ProductSourceType
    status: ProductSourceStatus
    original_filename: str | None
    storage_key: str | None
    mime_type: str | None
    file_size_bytes: int | None
    checksum_sha256: str | None
    display_name: str | None
    text_content: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    version: int

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, UUID):
            raise ValueError("source_id must be a UUID")
        if not isinstance(self.product_id, UUID):
            raise ValueError("product_id must be a UUID")
        if not isinstance(self.source_type, ProductSourceType):
            raise ValueError("source_type must be a ProductSourceType")
        if not isinstance(self.status, ProductSourceStatus):
            raise ValueError("status must be a ProductSourceStatus")

        filename = _optional_text(
            self.original_filename, "original_filename", ORIGINAL_FILENAME_MAX_LENGTH
        )
        if filename is not None and ("/" in filename or "\\" in filename):
            raise ValueError("original_filename must not contain a path")
        storage_key = _optional_text(self.storage_key, "storage_key", STORAGE_KEY_MAX_LENGTH)
        if storage_key is not None and (
            storage_key.startswith(("/", "\\")) or _WINDOWS_ABSOLUTE_PATTERN.match(storage_key)
        ):
            raise ValueError("storage_key must be relative")
        if storage_key is not None and any(
            marker in storage_key.lower()
            for marker in ("aws_access_key", "aws_secret", "x-amz-credential", "password=")
        ):
            raise ValueError("storage_key must not contain credentials")
        mime_type = _optional_text(self.mime_type, "mime_type", MIME_TYPE_MAX_LENGTH)
        if mime_type is not None:
            mime_type = mime_type.lower()
        checksum = _optional_text(self.checksum_sha256, "checksum_sha256", 64)
        if checksum is not None:
            if not _CHECKSUM_PATTERN.fullmatch(checksum):
                raise ValueError("checksum_sha256 must contain exactly 64 hexadecimal characters")
            checksum = checksum.lower()

        if self.file_size_bytes is not None:
            if isinstance(self.file_size_bytes, bool) or not isinstance(self.file_size_bytes, int):
                raise ValueError("file_size_bytes must be an integer or null")
            if self.file_size_bytes < 0:
                raise ValueError("file_size_bytes must be non-negative")

        text_content = _optional_text(self.text_content, "text_content", TEXT_CONTENT_MAX_LENGTH)
        if self.source_type is not ProductSourceType.TEXT:
            if filename is None:
                raise ValueError("original_filename is required for file sources")
            if text_content is not None:
                raise ValueError("text_content is allowed only for TEXT sources")
        if mime_type is not None and mime_type not in _ALLOWED_MIME_TYPES[self.source_type]:
            raise ValueError("mime_type is incompatible with source_type")

        object.__setattr__(self, "original_filename", filename)
        object.__setattr__(self, "storage_key", storage_key)
        object.__setattr__(self, "mime_type", mime_type)
        object.__setattr__(self, "checksum_sha256", checksum)
        object.__setattr__(
            self,
            "display_name",
            _optional_text(self.display_name, "display_name", DISPLAY_NAME_MAX_LENGTH),
        )
        object.__setattr__(self, "text_content", text_content)
        object.__setattr__(
            self,
            "error_message",
            _optional_text(self.error_message, "error_message", ERROR_MESSAGE_MAX_LENGTH),
        )
        object.__setattr__(self, "created_at", _utc_datetime(self.created_at, "created_at"))
        object.__setattr__(self, "updated_at", _utc_datetime(self.updated_at, "updated_at"))
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise ValueError("version must be a positive integer")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot precede created_at")

    @classmethod
    def create(
        cls,
        *,
        product_id: UUID,
        source_type: ProductSourceType,
        original_filename: str | None = None,
        storage_key: str | None = None,
        mime_type: str | None = None,
        file_size_bytes: int | None = None,
        checksum_sha256: str | None = None,
        display_name: str | None = None,
        text_content: str | None = None,
        now: datetime | None = None,
    ) -> Self:
        timestamp = _utc_datetime(now or datetime.now(UTC), "now")
        return cls(
            source_id=uuid4(),
            product_id=product_id,
            source_type=source_type,
            status=ProductSourceStatus.PENDING,
            original_filename=original_filename,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            checksum_sha256=checksum_sha256,
            display_name=display_name,
            text_content=text_content,
            error_message=None,
            created_at=timestamp,
            updated_at=timestamp,
            version=1,
        )


@dataclass(frozen=True, slots=True)
class ProductSourcePage:
    items: tuple[ProductSource, ...]
    next_cursor: str | None
