"""Image-analysis schema and DynamoDB serialization tests."""

import pytest

from app.core.exceptions import ImageAnalysisSerializationError
from app.schemas.image_analysis.models import ImageAnalysisResultRecord
from app.utils.dynamodb import (
    deserialize_item,
    image_analysis_metadata_to_item,
    image_analysis_region_to_item,
    image_analysis_result_from_items,
    serialize_item,
)
from tests.fixtures.image_analysis import make_image_analysis_result


def records():
    result = make_image_analysis_result()
    return result, [image_analysis_metadata_to_item(result)] + [
        image_analysis_region_to_item(result.analysis_id, index, region)
        for index, region in enumerate(result.regions, start=1)
    ]


def test_meta_and_region_records_round_trip_in_order() -> None:
    result, raw = records()
    restored = image_analysis_result_from_items(
        [deserialize_item(serialize_item(item)) for item in raw]
    )
    assert restored == result
    assert raw[1]["recordKey"] == "REGION#000001"
    assert raw[-1]["recordKey"] == "REGION#000006"


def test_schema_uses_camel_case_and_integer_coordinates() -> None:
    record = ImageAnalysisResultRecord.model_validate(make_image_analysis_result())
    payload = record.model_dump(mode="json", by_alias=True)
    assert payload["metadata"]["aspectRatioNumerator"] == 400
    assert payload["regions"][0]["relativeWidthBp"] == 10_000


@pytest.mark.parametrize("mutation", ["no_meta", "missing_region", "bad_metadata", "bad_region"])
def test_malformed_or_incomplete_records_are_controlled(mutation: str) -> None:
    _, raw = records()
    if mutation == "no_meta":
        raw = raw[1:]
    elif mutation == "missing_region":
        raw = raw[:-1]
    elif mutation == "bad_metadata":
        raw[0]["pixelCount"] = 1
    else:
        raw[1]["width"] = 0
    wire = [deserialize_item(serialize_item(item)) for item in raw]
    with pytest.raises(ImageAnalysisSerializationError):
        image_analysis_result_from_items(wire)


def test_persistence_records_contain_no_floats() -> None:
    _, raw = records()

    def contains_float(value: object) -> bool:
        if isinstance(value, float):
            return True
        if isinstance(value, dict):
            return any(contains_float(item) for item in value.values())
        if isinstance(value, (list, tuple)):
            return any(contains_float(item) for item in value)
        return False

    assert not any(contains_float(item) for item in raw)
