"""Product-source item serialization tests."""

from decimal import Decimal

import pytest

from app.core.exceptions import ProductSerializationError, ProductSourceSerializationError
from app.domain.product_sources import ProductSourceStatus
from app.utils.dynamodb import (
    deserialize_item,
    product_source_from_item,
    product_source_to_item,
    serialize_item,
)
from tests.fixtures.product_sources import SOURCE_ID, make_product_source
from tests.fixtures.products import PRODUCT_ID


def test_product_source_item_round_trip_preserves_domain_values() -> None:
    source = make_product_source(checksum_sha256="a" * 64)
    compatible = deserialize_item(serialize_item(product_source_to_item(source)))
    restored = product_source_from_item(compatible)
    assert restored == source
    assert compatible["sourceId"] == str(SOURCE_ID)
    assert compatible["productId"] == str(PRODUCT_ID)
    assert compatible["status"] == ProductSourceStatus.PENDING.value
    assert compatible["storageKey"] is None
    assert compatible["fileSizeBytes"] == Decimal(102_400)
    assert compatible["createdAt"].endswith("Z")


def test_product_source_item_contains_metadata_only() -> None:
    item = product_source_to_item(make_product_source())
    assert set(item) == {
        "productId",
        "sourceId",
        "sourceType",
        "status",
        "originalFilename",
        "storageKey",
        "mimeType",
        "fileSizeBytes",
        "checksumSha256",
        "displayName",
        "textContent",
        "errorMessage",
        "version",
        "createdAt",
        "updatedAt",
    }
    assert "fileBytes" not in item
    assert "extractedText" not in item


def test_central_serializer_still_rejects_python_floats() -> None:
    with pytest.raises(ProductSerializationError):
        serialize_item({"fileSizeBytes": 1.5})


@pytest.mark.parametrize(
    "mutation",
    [
        lambda item: item.pop("productId"),
        lambda item: item.pop("sourceId"),
        lambda item: item.update(sourceType="URL"),
        lambda item: item.update(fileSizeBytes=Decimal("1.5")),
        lambda item: item.update(createdAt="not-a-date"),
    ],
)
def test_malformed_source_items_raise_controlled_error(mutation: object) -> None:
    item = product_source_to_item(make_product_source())
    mutation(item)  # type: ignore[operator]
    with pytest.raises(ProductSourceSerializationError):
        product_source_from_item(item)
