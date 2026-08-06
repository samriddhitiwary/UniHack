"""Product entity and enum tests."""

from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.domain.products import Product, ProductCategory, ProductStatus
from tests.fixtures.products import make_product


def test_product_creation_generates_foundational_defaults() -> None:
    before = datetime.now(UTC)
    product = Product.create(name="  Industrial Motor  ", manufacturer="   ")
    after = datetime.now(UTC)

    assert isinstance(product.product_id, UUID)
    assert product.name == "Industrial Motor"
    assert product.manufacturer is None
    assert product.category is ProductCategory.UNCLASSIFIED
    assert product.status is ProductStatus.DRAFT
    assert product.source_count == 0
    assert product.version == 1
    assert before <= product.created_at == product.updated_at <= after
    assert product.created_at.tzinfo is UTC


def test_product_identity_and_creation_time_are_immutable() -> None:
    product = make_product()
    with pytest.raises(FrozenInstanceError):
        product.name = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize("name", ["", " ", "X"])
def test_product_rejects_non_meaningful_name(name: str) -> None:
    with pytest.raises(ValueError, match="name"):
        Product.create(name=name)


def test_product_rejects_invalid_category() -> None:
    product = make_product()
    values = {field.name: getattr(product, field.name) for field in fields(product)}
    values["category"] = "UNKNOWN"
    with pytest.raises(ValueError, match="category"):
        Product(**values)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [("source_count", -1, "non-negative"), ("version", 0, "positive")],
)
def test_product_rejects_invalid_numeric_invariants(field: str, value: int, message: str) -> None:
    product = make_product()
    values = {item.name: getattr(product, item.name) for item in fields(product)}
    values[field] = value
    with pytest.raises(ValueError, match=message):
        Product(**values)


def test_product_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Product.create(name="Valid product", now=datetime(2026, 8, 6, 12, 0))


def test_product_enums_are_readable_json_strings() -> None:
    assert ProductCategory.CENTRIFUGAL_PUMP.value == "CENTRIFUGAL_PUMP"
    assert ProductStatus.READY_TO_PUBLISH.value == "READY_TO_PUBLISH"
