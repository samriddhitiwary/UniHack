"""PDF table DynamoDB and schema serialization tests."""

from dataclasses import replace

import pytest

from app.core.exceptions import PdfTableExtractionSerializationError
from app.schemas.pdf_table_extraction.models import PdfTableExtractionResultRecord
from app.utils.dynamodb import (
    deserialize_item,
    pdf_table_extraction_metadata_to_item,
    pdf_table_extraction_result_from_items,
    pdf_table_extraction_table_to_item,
    serialize_item,
)
from tests.fixtures.pdf_table_extraction import make_pdf_table_extraction_result


def test_metadata_and_nested_table_records_round_trip() -> None:
    result = make_pdf_table_extraction_result()
    records = [pdf_table_extraction_metadata_to_item(result)] + [
        pdf_table_extraction_table_to_item(result.extraction_id, table) for table in result.tables
    ]
    restored = pdf_table_extraction_result_from_items(
        [deserialize_item(serialize_item(record)) for record in records]
    )
    assert restored == result
    assert records[1]["recordKey"] == "TABLE#000001#000001"
    assert records[2]["recordKey"] == "TABLE#000002#000001"


def test_internal_schema_uses_camel_case_and_preserves_empty_strings() -> None:
    result = make_pdf_table_extraction_result()
    record = PdfTableExtractionResultRecord.model_validate(result)
    payload = record.model_dump(mode="json", by_alias=True)
    assert payload["extractionId"] == str(result.extraction_id)
    assert payload["tables"][0]["rows"][0]["cells"][0]["text"] == "Model"


@pytest.mark.parametrize(
    "records",
    [
        [],
        [{"recordKey": "META"}],
        [pdf_table_extraction_metadata_to_item(make_pdf_table_extraction_result())],
    ],
)
def test_missing_or_incomplete_records_are_controlled(records: list[dict[str, object]]) -> None:
    with pytest.raises(PdfTableExtractionSerializationError):
        pdf_table_extraction_result_from_items(records)


def test_malformed_nested_cell_is_controlled() -> None:
    result = make_pdf_table_extraction_result()
    metadata = pdf_table_extraction_metadata_to_item(result)
    table = pdf_table_extraction_table_to_item(result.extraction_id, result.tables[0])
    malformed = replace(result.tables[1], page_number=1, table_index=2)
    second = pdf_table_extraction_table_to_item(result.extraction_id, malformed)
    table["rows"] = [{"rowIndex": 0, "cells": ["bad"]}]
    with pytest.raises(PdfTableExtractionSerializationError):
        pdf_table_extraction_result_from_items([metadata, table, second])
