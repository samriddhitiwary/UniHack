"""PDF extraction DynamoDB mapping and schema tests."""

from dataclasses import replace

import pytest

from app.core.exceptions import PdfExtractionSerializationError, ProductSerializationError
from app.schemas.pdf_extraction import PdfTextExtractionResultRecord
from app.utils.dynamodb import (
    deserialize_item,
    pdf_extraction_metadata_to_item,
    pdf_extraction_page_to_item,
    pdf_extraction_result_from_items,
    serialize_item,
)
from tests.fixtures.pdf_extraction import make_pdf_extraction_result


def round_trip_items() -> list[dict[str, object]]:
    result = make_pdf_extraction_result()
    native = [pdf_extraction_metadata_to_item(result)] + [
        pdf_extraction_page_to_item(result.extraction_id, page) for page in result.pages
    ]
    return [deserialize_item(serialize_item(item)) for item in native]


def test_metadata_and_page_records_round_trip_to_domain() -> None:
    result = make_pdf_extraction_result()
    restored = pdf_extraction_result_from_items(round_trip_items())
    assert restored == result
    metadata, first_page = round_trip_items()[:2]
    assert metadata["recordKey"] == "META" and "pages" not in metadata
    assert first_page["recordKey"] == "PAGE#000001"
    assert "jobId" not in first_page and "createdAt" not in first_page


def test_result_schema_serializes_camel_case_page_evidence() -> None:
    record = PdfTextExtractionResultRecord.model_validate(make_pdf_extraction_result())
    body = record.model_dump(mode="json", by_alias=True)
    assert body["qualityStatus"] == "USABLE"
    assert body["pages"][0]["pageNumber"] == 1
    assert body["pages"][0]["characterCount"] == len(body["pages"][0]["text"])


@pytest.mark.parametrize(
    "mutator",
    [
        lambda items: [item for item in items if item["recordKey"] != "META"],
        lambda items: [item for item in items if item["recordKey"] != "PAGE#000002"],
        lambda items: [{**items[0], "qualityStatus": "BROKEN"}, *items[1:]],
        lambda items: [{**items[0], "warningCodes": "not-a-list"}, *items[1:]],
    ],
)
def test_malformed_records_raise_controlled_serialization_error(mutator: object) -> None:
    items = mutator(round_trip_items())  # type: ignore[operator]
    with pytest.raises(PdfExtractionSerializationError):
        pdf_extraction_result_from_items(items)


def test_float_remains_rejected_for_extraction_items() -> None:
    metadata = pdf_extraction_metadata_to_item(make_pdf_extraction_result())
    with pytest.raises(ProductSerializationError):
        serialize_item({**metadata, "unsafe": 1.5})


def test_domain_rejects_inconsistent_summary() -> None:
    with pytest.raises(ValueError):
        replace(make_pdf_extraction_result(), total_character_count=999)
