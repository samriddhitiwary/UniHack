"""Flat catalog CSV serializer tests."""

import csv
import io
from dataclasses import replace

from app.services.catalog_csv_exporter import FIXED_COLUMNS, CatalogCsvExporter
from tests.fixtures.catalog_export import export_result


def _rows(content: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(content.decode("utf-8"), newline="")))


def test_csv_is_deterministic_utf8_one_product_row_and_lf_only() -> None:
    _, projection, _, _ = export_result()
    exporter = CatalogCsvExporter()
    first = exporter.serialize(projection=projection)
    assert first == exporter.serialize(projection=projection)
    assert b"\r" not in first and not first.startswith(b"\xef\xbb\xbf")
    rows = _rows(first)
    assert len(rows) == 2
    assert tuple(rows[0][: len(FIXED_COLUMNS)]) == FIXED_COLUMNS


def test_csv_attributes_follow_projection_order_with_only_present_unit_columns() -> None:
    _, projection, _, _ = export_result()
    headers, row = _rows(CatalogCsvExporter().serialize(projection=projection))
    tail = headers[len(FIXED_COLUMNS) :]
    expected: list[str] = []
    for item in projection.attributes:
        expected.append(item.attribute_name)
        if item.unit is not None:
            expected.append(f"{item.attribute_name}Unit")
    assert tail == expected
    phase_index = headers.index("phase")
    assert row[phase_index] == "3" and "phaseUnit" not in headers


def test_csv_missing_identity_warning_and_null_unit_semantics() -> None:
    _, projection, _, _ = export_result(manufacturer=None, model_number=None, description=None)
    headers, row = _rows(CatalogCsvExporter().serialize(projection=projection))
    mapped = dict(zip(headers, row, strict=True))
    assert mapped["manufacturer"] == mapped["modelNumber"] == mapped["description"] == ""
    assert mapped["warningReasonCodes"] == (
        "MANUFACTURER_MISSING|MODEL_NUMBER_MISSING|DESCRIPTION_MISSING"
    )


def test_csv_standard_library_round_trips_commas_quotes_newlines_and_unicode() -> None:
    _, projection, _, _ = export_result()
    special = replace(projection, description='Heavy duty, "high efficiency"\nMotor Ω')
    headers, row = _rows(CatalogCsvExporter().serialize(projection=special))
    assert dict(zip(headers, row, strict=True))["description"] == (
        'Heavy duty, "high efficiency"\nMotor Ω'
    )
