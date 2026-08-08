"""CSV parser dialect, evidence, malformed-row, and safety-limit tests."""

from io import BytesIO

import pytest

from app.core.exceptions import (
    CsvCellLimitExceededError,
    CsvCellTextLimitExceededError,
    CsvColumnLimitExceededError,
    CsvDelimiterUndeterminedError,
    CsvEmptyFileError,
    CsvEncodingUnsupportedError,
    CsvFileSizeLimitExceededError,
    CsvParseError,
    CsvRowLimitExceededError,
)
from app.services.csv_parser import CsvParser, CsvProcessingLimits


def parser(**changes: int) -> CsvParser:
    values = dict(
        max_file_bytes=10_000,
        max_rows=20,
        max_columns=20,
        max_total_cells=100,
        max_cell_characters=100,
        sample_bytes=1_000,
    )
    values.update(changes)
    return CsvParser(CsvProcessingLimits(**values))


def parse(text: str, **limits: int):
    return parser(**limits).parse(BytesIO(text.encode("utf-8")))


def test_standard_comma_csv_preserves_header_rows_and_strings() -> None:
    result = parse("manufacturer,model,power\nABC,00123,5 kW\n")
    assert [cell.text for cell in result.header] == ["manufacturer", "model", "power"]
    assert [cell.text for cell in result.rows[0].cells] == ["ABC", "00123", "5 kW"]
    assert result.rows[0].row_number == 1 and result.delimiter == ","


def test_utf8_and_bom_are_supported() -> None:
    content = "name,café\nPump,Crème\n".encode()
    assert parser().parse(BytesIO(content)).header[1].text == "café"
    result = parser().parse(BytesIO(b"\xef\xbb\xbf" + content))
    assert result.header[0].text == "name" and result.encoding == "utf-8"


@pytest.mark.parametrize("delimiter", [";", "\t", "|"])
def test_allowlisted_alternate_delimiters(delimiter: str) -> None:
    result = parse(f"name{delimiter}model\nPump{delimiter}PX-1\n")
    assert result.delimiter == delimiter
    assert [cell.text for cell in result.rows[0].cells] == ["Pump", "PX-1"]


def test_standard_quoting_delimiters_quotes_and_multiline_fields() -> None:
    result = parse('name,notes\n"Pump, Series","Line 1\nLine 2"\n"Valve ""A""",ok\n')
    assert result.rows[0].cells[0].text == "Pump, Series"
    assert result.rows[0].cells[1].text == "Line 1\nLine 2"
    assert result.rows[1].cells[0].text == 'Valve "A"'


def test_blank_duplicate_and_empty_headers_are_preserved() -> None:
    result = parse("name,,name\nA,,B\n")
    assert [cell.text for cell in result.header] == ["name", "", "name"]
    assert result.header[1].is_empty and result.rows[0].cells[1].is_empty


def test_header_only_csv_is_valid() -> None:
    result = parse("manufacturer,model,power\n")
    assert len(result.header) == 3 and result.rows == ()


@pytest.mark.parametrize("content", [b"", b"\xef\xbb\xbf", b"\n\r\n"])
def test_empty_csv_fails(content: bytes) -> None:
    with pytest.raises(CsvEmptyFileError):
        parser().parse(BytesIO(content))


def test_short_and_extra_rows_preserve_evidence_and_warnings() -> None:
    result = parse("A,B,C\n1,2\n3,4,5,6\n")
    short, extra = result.rows
    assert [cell.text for cell in short.cells] == ["1", "2", ""]
    assert short.warning_codes == ("CSV_ROW_MISSING_COLUMNS",)
    assert [cell.text for cell in extra.cells] == ["3", "4", "5"]
    assert [cell.text for cell in extra.extra_cells] == ["6"]
    assert extra.warning_codes == ("CSV_ROW_EXTRA_COLUMNS",)


def test_blank_physical_lines_ignored_but_quoted_empty_row_preserved() -> None:
    result = parse('A,B\n\n""\n\r\n1,2\n')
    assert len(result.rows) == 2
    assert result.rows[0].cells[0].is_empty and result.rows[0].is_malformed
    assert [cell.text for cell in result.rows[1].cells] == ["1", "2"]


def test_normalization_preserves_internal_text_and_formula_looking_values() -> None:
    result = parse('id,value\n00123," 5  kW "\n2,"=SUM(A1:A2)"\n3,+10\n4,-2\n5,@name\n')
    values = [row.cells[1].text for row in result.rows]
    assert values == ["5  kW", "=SUM(A1:A2)", "+10", "-2", "@name"]


def test_invalid_utf8_unknown_delimiter_and_malformed_quotes_are_controlled() -> None:
    with pytest.raises(CsvEncodingUnsupportedError):
        parser().parse(BytesIO(b"a,b\n\xff,x"))
    with pytest.raises(CsvDelimiterUndeterminedError):
        parse("header value\ndata value\n")
    with pytest.raises(CsvParseError):
        parse('A,B\n"unterminated,value\n')


def test_file_row_column_cell_and_text_limits_fail_without_truncation() -> None:
    with pytest.raises(CsvFileSizeLimitExceededError):
        parse("A,B\n1,2\n", max_file_bytes=5)
    with pytest.raises(CsvRowLimitExceededError):
        parse("A,B\n1,2\n3,4\n", max_rows=1)
    with pytest.raises(CsvColumnLimitExceededError):
        parse("A,B,C\n1,2,3\n", max_columns=2)
    with pytest.raises(CsvColumnLimitExceededError):
        parse("A,B\n1,2,3\n", max_columns=2)
    with pytest.raises(CsvCellLimitExceededError):
        parse("A,B\n1,2\n3,4\n", max_total_cells=3)
    with pytest.raises(CsvCellTextLimitExceededError):
        parse("A,B\nlong,2\n", max_cell_characters=3)
    with pytest.raises(CsvCellTextLimitExceededError):
        parse("long,B\n1,2\n", max_cell_characters=3)


@pytest.mark.parametrize(
    "field",
    [
        "max_file_bytes",
        "max_rows",
        "max_columns",
        "max_total_cells",
        "max_cell_characters",
        "sample_bytes",
    ],
)
def test_limits_must_be_positive(field: str) -> None:
    values = dict(
        max_file_bytes=1,
        max_rows=1,
        max_columns=1,
        max_total_cells=1,
        max_cell_characters=1,
        sample_bytes=1,
    )
    values[field] = 0
    with pytest.raises(ValueError):
        CsvProcessingLimits(**values)
