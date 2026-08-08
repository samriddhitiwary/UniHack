"""CSV processing schema and DynamoDB serialization tests."""

import pytest

from app.core.exceptions import CsvProcessingSerializationError
from app.schemas.csv_processing.models import CsvProcessingResultRecord
from app.utils.dynamodb import (
    csv_processing_metadata_to_item,
    csv_processing_result_from_items,
    csv_processing_row_to_item,
    deserialize_item,
    serialize_item,
)
from tests.fixtures.csv_processing import make_csv_processing_result


def records():
    result = make_csv_processing_result()
    return result, [csv_processing_metadata_to_item(result)] + [
        csv_processing_row_to_item(result.processing_id, row) for row in result.rows
    ]


def test_meta_header_rows_and_extra_cells_round_trip() -> None:
    result, raw_records = records()
    wire_round_trip = [deserialize_item(serialize_item(record)) for record in raw_records]
    restored = csv_processing_result_from_items(wire_round_trip)
    assert restored == result
    assert raw_records[1]["recordKey"] == "ROW#000000001"
    assert raw_records[2]["recordKey"] == "ROW#000000002"


def test_internal_schema_serializes_camel_case_and_strings() -> None:
    record = CsvProcessingResultRecord.model_validate(make_csv_processing_result())
    payload = record.model_dump(mode="json", by_alias=True)
    assert payload["processingId"] == str(record.processing_id)
    assert payload["rows"][0]["cells"][1]["text"] == "00123"


@pytest.mark.parametrize("mutation", ["no_meta", "missing_row", "bad_header", "bad_warning"])
def test_malformed_or_incomplete_records_are_controlled(mutation: str) -> None:
    _, raw_records = records()
    if mutation == "no_meta":
        raw_records = raw_records[1:]
    elif mutation == "missing_row":
        raw_records = raw_records[:-1]
    elif mutation == "bad_header":
        raw_records[0]["header"] = "bad"
    else:
        raw_records[1]["warningCodes"] = "bad"
    wire = [deserialize_item(serialize_item(record)) for record in raw_records]
    with pytest.raises(CsvProcessingSerializationError):
        csv_processing_result_from_items(wire)


def test_header_only_result_round_trip() -> None:
    result = make_csv_processing_result(rows=())
    metadata = deserialize_item(serialize_item(csv_processing_metadata_to_item(result)))
    assert csv_processing_result_from_items([metadata]) == result


def test_persistence_records_contain_no_floats() -> None:
    _, raw_records = records()

    def contains_float(value: object) -> bool:
        if isinstance(value, float):
            return True
        if isinstance(value, dict):
            return any(contains_float(item) for item in value.values())
        if isinstance(value, (list, tuple)):
            return any(contains_float(item) for item in value)
        return False

    assert not any(contains_float(record) for record in raw_records)
