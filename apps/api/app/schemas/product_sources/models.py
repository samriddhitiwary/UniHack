"""Pydantic schemas for product-source repository boundaries."""

import re
import string
from typing import ClassVar, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.json_schema import SkipJsonSchema

from app.domain.product_sources import ProductSource, ProductSourceStatus, ProductSourceType
from app.domain.product_sources.entities import (
    DISPLAY_NAME_MAX_LENGTH,
    ERROR_MESSAGE_MAX_LENGTH,
    MIME_TYPE_MAX_LENGTH,
    ORIGINAL_FILENAME_MAX_LENGTH,
    STORAGE_KEY_MAX_LENGTH,
    TEXT_CONTENT_MAX_LENGTH,
)
from app.schemas.products.models import to_camel

_WINDOWS_ABSOLUTE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")


class ProductSourceSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
        str_strip_whitespace=True,
    )

    @field_validator(
        "original_filename",
        "storage_key",
        "mime_type",
        "checksum_sha256",
        "display_name",
        "text_content",
        "error_message",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def blank_optional_text_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("mime_type", "checksum_sha256", check_fields=False)
    @classmethod
    def normalized_lowercase(cls, value: str | None) -> str | None:
        return value.lower() if value is not None else None

    @field_validator("checksum_sha256", check_fields=False)
    @classmethod
    def valid_checksum(cls, value: str | None) -> str | None:
        if value is not None and (
            len(value) != 64 or any(character not in string.hexdigits for character in value)
        ):
            raise ValueError("checksum_sha256 must contain exactly 64 hexadecimal characters")
        return value

    @field_validator("storage_key", check_fields=False)
    @classmethod
    def safe_storage_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        lowered = value.lower()
        if value.startswith(("/", "\\")) or _WINDOWS_ABSOLUTE_PATTERN.match(value):
            raise ValueError("storage_key must be relative")
        if any(
            marker in lowered
            for marker in ("aws_access_key", "aws_secret", "x-amz-credential", "password=")
        ):
            raise ValueError("storage_key must not contain credentials")
        return value


class ProductSourceCreate(ProductSourceSchema):
    product_id: UUID
    source_type: ProductSourceType
    original_filename: str | None = Field(default=None, max_length=ORIGINAL_FILENAME_MAX_LENGTH)
    storage_key: str | None = Field(default=None, max_length=STORAGE_KEY_MAX_LENGTH)
    mime_type: str | None = Field(default=None, max_length=MIME_TYPE_MAX_LENGTH)
    file_size_bytes: int | None = Field(default=None, ge=0, strict=True)
    checksum_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    display_name: str | None = Field(default=None, max_length=DISPLAY_NAME_MAX_LENGTH)
    text_content: str | None = Field(default=None, max_length=TEXT_CONTENT_MAX_LENGTH)

    @model_validator(mode="after")
    def validate_source_metadata(self) -> Self:
        ProductSource.create(**self.model_dump(by_alias=False))
        return self


class ProductSourceUpdate(ProductSourceSchema):
    editable_fields: ClassVar[frozenset[str]] = frozenset(
        {
            "status",
            "storage_key",
            "mime_type",
            "file_size_bytes",
            "checksum_sha256",
            "display_name",
            "text_content",
            "error_message",
        }
    )

    status: ProductSourceStatus | SkipJsonSchema[None] = None
    storage_key: str | None = Field(default=None, max_length=STORAGE_KEY_MAX_LENGTH)
    mime_type: str | None = Field(default=None, max_length=MIME_TYPE_MAX_LENGTH)
    file_size_bytes: int | None = Field(default=None, ge=0, strict=True)
    checksum_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    display_name: str | None = Field(default=None, max_length=DISPLAY_NAME_MAX_LENGTH)
    text_content: str | None = Field(default=None, max_length=TEXT_CONTENT_MAX_LENGTH)
    error_message: str | None = Field(default=None, max_length=ERROR_MESSAGE_MAX_LENGTH)

    @model_validator(mode="after")
    def validate_supplied_fields(self) -> Self:
        supplied = self.model_fields_set & self.editable_fields
        if not supplied:
            raise ValueError("at least one editable source field is required")
        if "status" in supplied and self.status is None:
            raise ValueError("status cannot be null")
        return self


class ProductSourceRecord(ProductSourceSchema):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    source_id: UUID
    product_id: UUID
    source_type: ProductSourceType
    status: ProductSourceStatus
    original_filename: str | None = Field(max_length=ORIGINAL_FILENAME_MAX_LENGTH)
    storage_key: str | None = Field(max_length=STORAGE_KEY_MAX_LENGTH)
    mime_type: str | None = Field(max_length=MIME_TYPE_MAX_LENGTH)
    file_size_bytes: int | None = Field(ge=0)
    checksum_sha256: str | None = Field(min_length=64, max_length=64)
    display_name: str | None = Field(max_length=DISPLAY_NAME_MAX_LENGTH)
    text_content: str | None = Field(max_length=TEXT_CONTENT_MAX_LENGTH)
    error_message: str | None = Field(max_length=ERROR_MESSAGE_MAX_LENGTH)
    created_at: AwareDatetime
    updated_at: AwareDatetime
    version: int = Field(ge=1)


class ProductSourceListResult(ProductSourceSchema):
    items: list[ProductSourceRecord]
    next_cursor: str | None = None
