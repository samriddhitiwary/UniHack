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
    schema = ProductUpdate(version=2, manufacturer=" ", status=ProductStatus.PROCESSING)
    assert schema.manufacturer is None
    assert schema.status is ProductStatus.PROCESSING
    assert schema.model_fields_set == {"version", "manufacturer", "status"}


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Updated name"},
        {"version": 0, "name": "Updated name"},
        {"version": -1, "name": "Updated name"},
        {"version": "abc", "name": "Updated name"},
        {"version": None, "name": "Updated name"},
        {"version": True, "name": "Updated name"},
        {"version": 1},
        {"version": 1, "name": None},
        {"version": 1, "category": None},
        {"version": 1, "status": None},
    ],
)
def test_product_update_requires_version_editable_field_and_valid_non_null_values(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ProductUpdate.model_validate(payload)


@pytest.mark.parametrize("field", ["manufacturer", "modelNumber", "description"])
def test_product_update_allows_explicit_null_for_nullable_fields(field: str) -> None:
    update = ProductUpdate.model_validate({"version": 3, field: None})
    expected_field = "model_number" if field == "modelNumber" else field
    assert update.model_fields_set == {"version", expected_field}


def test_schemas_reject_invalid_category_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ProductCreate(name="Valid product", category="FUTURE_CATEGORY")
    with pytest.raises(ValidationError):
        ProductUpdate(version=1, name="Valid name", unknown="value")


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
