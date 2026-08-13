"""Image OCR META/BLOCK DynamoDB serialization tests."""

from copy import deepcopy

import pytest

from app.core.exceptions import ImageOcrSerializationError, ProductSerializationError
from app.schemas.image_ocr.models import ImageOcrResultRecord
from app.utils.dynamodb import (
    deserialize_item,
    image_ocr_block_to_item,
    image_ocr_metadata_to_item,
    image_ocr_result_from_items,
    serialize_item,
)
from tests.fixtures.image_ocr import make_image_ocr_result


def records():
    result = make_image_ocr_result()
    values = [image_ocr_metadata_to_item(result)] + [
        image_ocr_block_to_item(result.ocr_id, index, block)
        for index, block in enumerate(result.blocks, start=1)
    ]
    return result, values


def test_meta_and_block_records_round_trip_complete_result() -> None:
    result, values = records()
    assert (
        image_ocr_result_from_items([deserialize_item(serialize_item(value)) for value in values])
        == result
    )
    assert values[0]["recordKey"] == "META"
    assert values[1]["recordKey"] == "BLOCK#000001"
    assert values[1]["text"] == "MOTOR 415 V"
    assert values[1]["confidenceBp"] == 9_000


def test_internal_result_schema_uses_camel_case_and_integer_evidence() -> None:
    record = ImageOcrResultRecord.model_validate(make_image_ocr_result())
    payload = record.model_dump(mode="json", by_alias=True)
    assert payload["imageAnalysisId"]
    assert payload["averageConfidenceBp"] == 9_000
    assert payload["blocks"][0]["relativeWidthBp"] == 2_500


def test_serialized_records_contain_no_raw_python_float() -> None:
    _, values = records()
    for value in values:
        serialize_item(value)
    invalid = deepcopy(values[1])
    invalid["confidenceBp"] = 0.9
    with pytest.raises(ProductSerializationError):
        serialize_item(invalid)


@pytest.mark.parametrize("mutation", ["missing_meta", "missing_block", "bad_count", "gap"])
def test_incomplete_or_inconsistent_partitions_are_controlled(mutation: str) -> None:
    _, values = records()
    if mutation == "missing_meta":
        values = values[1:]
    elif mutation == "missing_block":
        values = values[:1]
    elif mutation == "bad_count":
        values[0]["blockCount"] = 2
    else:
        values[1]["recordKey"] = "BLOCK#000002"
    with pytest.raises(ImageOcrSerializationError):
        image_ocr_result_from_items(values)


@pytest.mark.parametrize(
    ("record", "field", "value"),
    [
        (0, "qualityStatus", "BAD"),
        (0, "createdAt", "not-a-time"),
        (0, "averageConfidenceBp", 10_001),
        (1, "x", -1),
        (1, "text", ""),
        (1, "relativeWidthBp", 0),
    ],
)
def test_malformed_meta_or_block_is_controlled(record: int, field: str, value: object) -> None:
    _, values = records()
    values[record][field] = value
    with pytest.raises(ImageOcrSerializationError):
        image_ocr_result_from_items(values)
