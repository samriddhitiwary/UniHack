"""Deterministic product-source fixtures."""

from datetime import UTC, datetime
from uuid import UUID

from app.domain.product_sources import ProductSource, ProductSourceStatus, ProductSourceType
from tests.fixtures.products import PRODUCT_ID

SOURCE_ID = UUID("f348db3c-4da2-47f8-8716-179b7dd9273c")
SECOND_SOURCE_ID = UUID("7449f3ca-1879-4ad4-b0d5-42d5c4534e0a")
SOURCE_CREATED_AT = datetime(2026, 8, 6, 15, 0, tzinfo=UTC)
SOURCE_UPDATED_AT = datetime(2026, 8, 6, 16, 0, tzinfo=UTC)


def make_product_source(
    *,
    source_id: UUID = SOURCE_ID,
    product_id: UUID = PRODUCT_ID,
    source_type: ProductSourceType = ProductSourceType.PDF,
    status: ProductSourceStatus = ProductSourceStatus.PENDING,
    original_filename: str | None = "pump-datasheet.pdf",
    storage_key: str | None = None,
    mime_type: str | None = "application/pdf",
    file_size_bytes: int | None = 102_400,
    checksum_sha256: str | None = None,
    display_name: str | None = "Pump Datasheet",
    text_content: str | None = None,
    error_message: str | None = None,
    created_at: datetime = SOURCE_CREATED_AT,
    updated_at: datetime = SOURCE_CREATED_AT,
    version: int = 1,
) -> ProductSource:
    return ProductSource(
        source_id=source_id,
        product_id=product_id,
        source_type=source_type,
        status=status,
        original_filename=original_filename,
        storage_key=storage_key,
        mime_type=mime_type,
        file_size_bytes=file_size_bytes,
        checksum_sha256=checksum_sha256,
        display_name=display_name,
        text_content=text_content,
        error_message=error_message,
        created_at=created_at,
        updated_at=updated_at,
        version=version,
    )
