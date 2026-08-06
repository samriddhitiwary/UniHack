"""Product Pydantic schema tests."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.products import ProductCategory, ProductStatus
from app.schemas.products import ProductCreate, ProductRecord, ProductUpdate


def test_product_create_accepts_only_caller_fields_and_normalizes_text() -> None:
    schema = ProductCreate(
        name="  PX-400 Pump  ",
        manufacturer="   ",
        model_number="  Px-400  ",
        category=ProductCategory.CENTRIFUGAL_PUMP,
    )
    assert schema.name == "PX-400 Pump"
    assert schema.manufacturer is None
    assert schema.model_number == "Px-400"
    assert schema.category is ProductCategory.CENTRIFUGAL_PUMP


@pytest.mark.parametrize("system_field", ["product_id", "created_at", "version", "source_count"])
def test_product_create_rejects_system_fields(system_field: str) -> None:
    with pytest.raises(ValidationError):
        ProductCreate(name="Valid product", **{system_field: "forbidden"})


def test_product_update_is_partial_and_tracks_explicit_null() -> None:
    schema = ProductUpdate(manufacturer=" ", status=ProductStatus.PROCESSING)
    assert schema.manufacturer is None
    assert schema.status is ProductStatus.PROCESSING
    assert schema.model_fields_set == {"manufacturer", "status"}


def test_schemas_reject_invalid_category_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ProductCreate(name="Valid product", category="FUTURE_CATEGORY")
    with pytest.raises(ValidationError):
        ProductUpdate(unknown="value")


def test_product_record_rejects_naive_timestamps() -> None:
    with pytest.raises(ValidationError):
        ProductRecord(
            product_id=uuid4(),
            name="Valid product",
            manufacturer=None,
            model_number=None,
            category=ProductCategory.UNCLASSIFIED,
            status=ProductStatus.DRAFT,
            description=None,
            source_count=0,
            created_at=datetime(2026, 8, 6, 12, 0),
            updated_at=datetime.now(UTC),
            version=1,
        )
