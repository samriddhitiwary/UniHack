"""Bounded parsing, exact schema, alignment, and import tests."""

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.core.exceptions import (
    UnilogChallengeInputNotFoundError,
    UnilogChallengeInputSchemaInvalidError,
    UnilogChallengeOutputNotFoundError,
    UnilogChallengeOutputSchemaInvalidError,
)
from app.domain.unilog_challenge import AlignmentStatus, ManufacturerParseStatus
from app.domain.unilog_challenge.delivery_schema import UNILOG_DELIVERY_HEADERS
from app.importers.unilog_challenge import (
    import_unilog_challenge_data,
    parse_expected_output_csv,
    parse_input_csv,
    write_import_artifact,
)

NOW = datetime(2026, 8, 21, tzinfo=UTC)


def _write_input(path: Path, rows: list[list[str]], headers: list[str] | None = None) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            headers
            or [
                "Mfg_Part_Num",
                "Part_Desc",
                "E1_Brand",
                "Unilog_Brand",
                "DIB_Brand",
                "Part_Manuf",
            ]
        )
        writer.writerows(rows)


def _write_output(
    path: Path,
    rows: list[dict[str, str]],
    headers: tuple[str, ...] = UNILOG_DELIVERY_HEADERS,
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _valid_input_rows() -> list[list[str]]:
    return [
        [
            "DCB518ASTS06G",
            'DCB518ASTS06G Diablo 1/2"x18" - Sanding Belt 6pc',
            "-- Unbranded --",
            "-- No Unilog Brand --",
            "-- No DIB Brand --",
            "Freud Inc (2435)",
        ],
        [
            "PDSH4816AF",
            "PDSH4816AF Dishwasher SS - Display Only",
            "-- Unbranded --",
            "-- No Unilog Brand --",
            "-- No DIB Brand --",
            "Appliance Dealers Cooperative (APPDE)",
        ],
    ]


def test_input_parser_preserves_raw_values_and_builds_stable_identity(tmp_path: Path) -> None:
    path = tmp_path / "input.csv"
    _write_input(path, _valid_input_rows())
    metadata, rows = parse_input_csv(path, imported_at=NOW)
    assert metadata.row_count == 2
    assert metadata.column_count == 6
    assert len(metadata.sha256) == 64
    assert rows[0].mfg_part_num == "DCB518ASTS06G"
    assert rows[0].part_desc == _valid_input_rows()[0][1]
    assert rows[0].e1_brand_raw == "-- Unbranded --"
    assert rows[0].e1_brand_clean is None
    assert rows[0].parsed_manufacturer == "Freud Inc"
    assert rows[0].source_reference_code == "2435"
    assert rows[0].manufacturer_parse_status is ManufacturerParseStatus.PARSED
    assert rows[0].row_id == parse_input_csv(path, imported_at=NOW)[1][0].row_id


def test_input_parser_handles_full_challenge_scale(tmp_path: Path) -> None:
    path = tmp_path / "input.csv"
    rows = [
        [
            f"PART-{index:04d}",
            f"Product description {index}",
            "-- Unbranded --",
            "-- No Unilog Brand --",
            "-- No DIB Brand --",
            f"Supplier {index % 10} (S{index % 10})",
        ]
        for index in range(1_000)
    ]
    _write_input(path, rows)
    metadata, parsed = parse_input_csv(path, imported_at=NOW)
    assert metadata.row_count == len(parsed) == 1_000
    assert len({row.row_id for row in parsed}) == 1_000


def test_expected_output_parser_preserves_exact_headers_blanks_and_symbols(
    tmp_path: Path,
) -> None:
    path = tmp_path / "output.csv"
    _write_output(
        path,
        [
            {
                "Mfg_Part_Num": "PDSH4816AF",
                "MANUFACTURER_NAME": "Rheem Manufacturing",
                "BRAND_NAME": "FRIGIDAIRE®",
                "Classpath": "Appliances>Dishwashers",
                "ATTRIBUTE_LABEL 1": "Voltage Rating",
                "ATTRIBUTE_UOM 1": "V",
            }
        ],
    )
    metadata, rows = parse_expected_output_csv(path, imported_at=NOW)
    assert metadata.column_count == 252
    assert rows[0].expected.value("BRAND_NAME") == "FRIGIDAIRE®"
    assert rows[0].expected.value("UPC") is None
    assert "UPC" not in rows[0].populated_fields
    assert tuple(rows[0].expected.as_dict()) == UNILOG_DELIVERY_HEADERS


def test_import_aligns_unique_rows_and_derives_incomplete_observed_vocabulary(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"
    _write_input(input_path, _valid_input_rows())
    _write_output(
        output_path,
        [
            {
                "Mfg_Part_Num": "PDSH4816AF",
                "MANUFACTURER_NAME": "Rheem Manufacturing",
                "BRAND_NAME": "FRIGIDAIRE®",
                "Classpath": "Appliances>Dishwashers",
                "ATTRIBUTE_LABEL 1": "Voltage Rating",
                "ATTRIBUTE_VALUE 1": "120",
                "ATTRIBUTE_UOM 1": "V",
            }
        ],
    )
    imported = import_unilog_challenge_data(input_path, output_path, imported_at=NOW)
    assert imported.statistics.aligned_rows == 1
    assert imported.statistics.unaligned_rows == 0
    assert imported.statistics.placeholder_values == 6
    assert imported.ground_truth_rows[0].input_row_id == imported.input_rows[1].row_id
    assert imported.observed_vocabulary.manufacturers == frozenset({"Rheem Manufacturing"})
    assert imported.observed_vocabulary.brands == frozenset({"FRIGIDAIRE®"})
    assert imported.observed_vocabulary.attribute_labels == frozenset({"Voltage Rating"})
    assert imported.observed_vocabulary.uoms == frozenset({"V"})


def test_duplicate_input_key_produces_ambiguous_alignment(tmp_path: Path) -> None:
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"
    duplicate = _valid_input_rows()[1]
    _write_input(input_path, [duplicate, [*duplicate[:1], "Different", *duplicate[2:]]])
    _write_output(output_path, [{"Mfg_Part_Num": "PDSH4816AF"}])
    imported = import_unilog_challenge_data(input_path, output_path, imported_at=NOW)
    assert imported.statistics.duplicate_input_keys == 1
    assert imported.statistics.ambiguous_rows == 1
    assert imported.alignments[0].status is AlignmentStatus.AMBIGUOUS_ALIGNMENT
    assert imported.alignments[0].aligned_input_row_id is None
    assert len(imported.alignments[0].candidate_row_ids) == 2


def test_unmatched_ground_truth_remains_explicit(tmp_path: Path) -> None:
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"
    _write_input(input_path, _valid_input_rows())
    _write_output(output_path, [{"Mfg_Part_Num": "UNKNOWN"}])
    imported = import_unilog_challenge_data(input_path, output_path, imported_at=NOW)
    assert imported.statistics.unaligned_rows == 1
    assert imported.alignments[0].status is AlignmentStatus.NOT_FOUND


def test_import_identity_is_independent_of_import_timestamp(tmp_path: Path) -> None:
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"
    _write_input(input_path, _valid_input_rows())
    _write_output(output_path, [{"Mfg_Part_Num": "PDSH4816AF"}])
    first = import_unilog_challenge_data(input_path, output_path, imported_at=NOW)
    second = import_unilog_challenge_data(
        input_path, output_path, imported_at=datetime(2027, 1, 1, tzinfo=UTC)
    )
    assert first.import_id == second.import_id
    assert first.input_rows == second.input_rows


def test_artifact_is_utf8_deterministic_and_contains_no_custom_delivery_columns(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"
    artifact = tmp_path / "nested" / "challenge.json"
    _write_input(input_path, _valid_input_rows())
    _write_output(output_path, [{"Mfg_Part_Num": "PDSH4816AF", "BRAND_NAME": "FRIGIDAIRE®"}])
    imported = import_unilog_challenge_data(input_path, output_path, imported_at=NOW)
    write_import_artifact(imported, artifact)
    first = artifact.read_bytes()
    write_import_artifact(imported, artifact)
    assert artifact.read_bytes() == first
    payload = json.loads(first)
    assert payload["importId"] == imported.import_id
    assert payload["groundTruthRows"][0]["expected"]["BRAND_NAME"] == "FRIGIDAIRE®"
    assert "AI Confidence" not in payload["groundTruthRows"][0]["expected"]


def test_missing_files_fail_with_controlled_codes(tmp_path: Path) -> None:
    with pytest.raises(UnilogChallengeInputNotFoundError) as input_error:
        parse_input_csv(tmp_path / "missing.csv", imported_at=NOW)
    assert input_error.value.code == "UNILOG_CHALLENGE_INPUT_NOT_FOUND"
    with pytest.raises(UnilogChallengeOutputNotFoundError) as output_error:
        parse_expected_output_csv(tmp_path / "missing.csv", imported_at=NOW)
    assert output_error.value.code == "UNILOG_CHALLENGE_OUTPUT_NOT_FOUND"


def test_input_parser_rejects_missing_header_and_malformed_width(tmp_path: Path) -> None:
    wrong = tmp_path / "wrong.csv"
    _write_input(wrong, [["P1"]], headers=["Mfg_Part_Num"])
    with pytest.raises(UnilogChallengeInputSchemaInvalidError):
        parse_input_csv(wrong, imported_at=NOW)
    malformed = tmp_path / "malformed.csv"
    _write_input(malformed, [["P1", "Description"]])
    with pytest.raises(UnilogChallengeInputSchemaInvalidError, match="wrong width"):
        parse_input_csv(malformed, imported_at=NOW)


def test_output_parser_rejects_missing_or_reordered_header(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    _write_output(missing, [], headers=UNILOG_DELIVERY_HEADERS[:-1])
    with pytest.raises(UnilogChallengeOutputSchemaInvalidError, match="252"):
        parse_expected_output_csv(missing, imported_at=NOW)
    reordered = tmp_path / "reordered.csv"
    headers = (UNILOG_DELIVERY_HEADERS[1], UNILOG_DELIVERY_HEADERS[0], *UNILOG_DELIVERY_HEADERS[2:])
    _write_output(reordered, [], headers=headers)
    with pytest.raises(UnilogChallengeOutputSchemaInvalidError, match="exact order"):
        parse_expected_output_csv(reordered, imported_at=NOW)


def test_required_input_and_ground_truth_values_cannot_be_blank(tmp_path: Path) -> None:
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"
    _write_input(input_path, [["", "Description", "", "", "", "Supplier"]])
    with pytest.raises(UnilogChallengeInputSchemaInvalidError, match="required"):
        parse_input_csv(input_path, imported_at=NOW)
    _write_output(output_path, [{"Mfg_Part_Num": "", "BRAND_NAME": "Unsupported"}])
    with pytest.raises(UnilogChallengeOutputSchemaInvalidError, match="Mfg_Part_Num"):
        parse_expected_output_csv(output_path, imported_at=NOW)
