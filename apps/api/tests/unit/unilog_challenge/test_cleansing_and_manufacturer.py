"""Challenge cleansing, manufacturer parsing, and evidence tests."""

import csv
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain.unilog_challenge import ManufacturerParseStatus, ResolutionStatus
from app.importers.unilog_challenge.parsers import parse_input_csv
from app.services.unilog_challenge import (
    EvidenceOnlyManufacturerResolver,
    clean_challenge_value,
    extract_brand_evidence,
    parse_part_manufacturer,
)


@pytest.mark.parametrize(
    "value",
    [
        "-- Unbranded --",
        " -- No Unilog Brand -- ",
        "-- No DIB Brand --",
        "",
        "   ",
        None,
    ],
)
def test_placeholders_and_blanks_become_missing(value: str | None) -> None:
    assert clean_challenge_value(value) is None


def test_meaningful_brand_text_is_only_trimmed() -> None:
    assert clean_challenge_value("  SOME BRAND®  ") == "SOME BRAND®"


@pytest.mark.parametrize(
    ("raw", "name", "code"),
    [
        ("Freud Inc (2435)", "Freud Inc", "2435"),
        ("Jam Industrial Supply LLC (JAMIN)", "Jam Industrial Supply LLC", "JAMIN"),
        ("Acme (USA) Corp (123)", "Acme (USA) Corp", "123"),
        ("A Company (ABC)  ", "A Company", "ABC"),
    ],
)
def test_final_parenthesized_reference_is_parsed(raw: str, name: str, code: str) -> None:
    parsed = parse_part_manufacturer(raw)
    assert parsed.raw == raw
    assert parsed.manufacturer_text == name
    assert parsed.source_reference_code == code
    assert parsed.status is ManufacturerParseStatus.PARSED


def test_internal_parentheses_are_not_destroyed() -> None:
    parsed = parse_part_manufacturer("Acme (USA) Corp")
    assert parsed.manufacturer_text == "Acme (USA) Corp"
    assert parsed.source_reference_code is None
    assert parsed.status is ManufacturerParseStatus.UNPARSED


def test_ambiguous_empty_final_reference_is_not_split() -> None:
    parsed = parse_part_manufacturer("Acme Corp ()")
    assert parsed.manufacturer_text == "Acme Corp ()"
    assert parsed.source_reference_code is None
    assert parsed.status is ManufacturerParseStatus.AMBIGUOUS


def test_missing_manufacturer_is_explicit() -> None:
    parsed = parse_part_manufacturer(None)
    assert parsed.manufacturer_text is None
    assert parsed.status is ManufacturerParseStatus.MISSING


def test_brand_evidence_deduplicates_clean_candidates_without_using_description(
    tmp_path: Path,
) -> None:
    path = tmp_path / "input.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "Mfg_Part_Num",
                "Part_Desc",
                "E1_Brand",
                "Unilog_Brand",
                "DIB_Brand",
                "Part_Manuf",
            ]
        )
        writer.writerow(
            ["P1", "3M product description", "Acme®", "Acme®", "-- No DIB Brand --", "Supplier (1)"]
        )
    _, rows = parse_input_csv(path, imported_at=datetime(2026, 1, 1, tzinfo=UTC))
    evidence = extract_brand_evidence(rows[0])
    assert evidence.candidate_brand_strings == ("Acme®",)
    assert evidence.description_text == "3M product description"


def test_evidence_only_resolution_never_claims_canonical_master(tmp_path: Path) -> None:
    path = tmp_path / "input.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ["Mfg_Part_Num", "Part_Desc", "E1_Brand", "Unilog_Brand", "DIB_Brand", "Part_Manuf"]
        )
        writer.writerow(
            ["P1", "3M item", "-- Unbranded --", "Brand A", "Brand B", "Supplier LLC (S1)"]
        )
    _, rows = parse_input_csv(path, imported_at=datetime(2026, 1, 1, tzinfo=UTC))
    result = EvidenceOnlyManufacturerResolver().resolve(rows[0], extract_brand_evidence(rows[0]))
    assert result.candidate_manufacturer == "Supplier LLC"
    assert result.candidate_brand is None
    assert result.status is ResolutionStatus.AMBIGUOUS
    assert result.review_required is True
    assert result.confidence_bp == 7_000
