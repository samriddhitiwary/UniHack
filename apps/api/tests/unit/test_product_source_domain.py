"""Product-source domain tests."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from app.domain.product_sources import ProductSource, ProductSourceStatus, ProductSourceType
from tests.fixtures.product_sources import make_product_source
from tests.fixtures.products import PRODUCT_ID


@pytest.mark.parametrize(
    ("source_type", "filename", "mime_type", "text_content"),
    [
        (ProductSourceType.PDF, "data.pdf", "application/pdf", None),
        (ProductSourceType.IMAGE, "photo.webp", "image/webp", None),
        (ProductSourceType.CSV, "data.csv", "text/csv", None),
        (ProductSourceType.TEXT, None, "text/plain", "manual input"),
    ],
)
def test_create_valid_source_types_with_defaults(
    source_type: ProductSourceType,
    filename: str | None,
    mime_type: str,
    text_content: str | None,
) -> None:
    now = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)
    source = ProductSource.create(
        product_id=PRODUCT_ID,
        source_type=source_type,
        original_filename=filename,
        mime_type=mime_type,
        text_content=text_content,
        now=now,
    )
    assert source.product_id == PRODUCT_ID
    assert source.status is ProductSourceStatus.PENDING
    assert source.version == 1
    assert source.source_id
    assert source.created_at == now
    assert source.updated_at == now


def test_source_normalizes_metadata() -> None:
    source = make_product_source(
        original_filename="  data.pdf  ",
        mime_type=" APPLICATION/PDF ",
        checksum_sha256="A" * 64,
        storage_key=" ",
        display_name=" ",
    )
    assert source.original_filename == "data.pdf"
    assert source.mime_type == "application/pdf"
    assert source.checksum_sha256 == "a" * 64
    assert source.storage_key is None
    assert source.display_name is None


@pytest.mark.parametrize(
    "changes",
    [
        {"checksum_sha256": "bad"},
        {"file_size_bytes": -1},
        {"file_size_bytes": True},
        {"text_content": "not allowed"},
        {"original_filename": None},
        {"mime_type": "image/png"},
        {"original_filename": "C:\\secret\\data.pdf"},
        {"storage_key": "/absolute/data.pdf"},
    ],
)
def test_file_source_rejects_invalid_metadata(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        make_product_source(**changes)  # type: ignore[arg-type]


def test_text_source_may_omit_filename_but_rejects_file_mime() -> None:
    source = make_product_source(
        source_type=ProductSourceType.TEXT,
        original_filename=None,
        mime_type="text/plain",
        file_size_bytes=None,
        text_content="Source notes",
    )
    assert source.text_content == "Source notes"
    with pytest.raises(ValueError):
        make_product_source(
            source_type=ProductSourceType.TEXT,
            original_filename=None,
            mime_type="application/pdf",
            file_size_bytes=None,
        )


def test_source_rejects_invalid_enums_timestamps_and_is_immutable() -> None:
    with pytest.raises(ValueError):
        make_product_source(source_type="URL")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        make_product_source(status="UNKNOWN")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        make_product_source(created_at=datetime(2026, 8, 6, 12, 0))
    source = make_product_source()
    with pytest.raises(FrozenInstanceError):
        source.status = ProductSourceStatus.READY  # type: ignore[misc]
