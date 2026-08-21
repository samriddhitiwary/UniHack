"""Bounded batch, exact UTF-8 CSV, CLI-compatible parse, and labelled regression tests."""

import csv
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain.unilog_challenge import BatchRowStatus
from app.domain.unilog_challenge.delivery_schema import UNILOG_DELIVERY_HEADERS
from app.importers.unilog_challenge.parsers import parse_expected_output_csv, parse_input_csv
from app.services.unilog_challenge.batch_enrichment import (
    UnilogBatchEnrichmentService,
    write_delivery_csv,
)
from app.services.unilog_challenge.enrichment_service import UnilogEnrichmentService
from app.services.unilog_challenge.ground_truth import compare_field, derive_observed_vocabulary
from tests.unit.unilog_challenge.helpers import challenge_row
from tests.unit.unilog_challenge.test_enrichment_extraction import vocabulary


def test_batch_preserves_order_statistics_and_exact_csv_without_internal_fields(
    tmp_path: Path,
) -> None:
    rows = (
        challenge_row(row_id="a" * 64),
        challenge_row(
            row_id="b" * 64,
            part="ABC",
            description="ABC Dishwasher SS",
            e1="FRIGIDAIRE®",
            dib="FRIGIDAIRE®",
            manufacturer="FRIGIDAIRE® (FRI01)",
        ),
    )
    batch = UnilogBatchEnrichmentService().enrich_batch(rows, vocabulary())
    assert [item.input_row_id for item in batch.rows] == ["a" * 64, "b" * 64]
    assert batch.statistics.total == 2
    assert batch.statistics.failed == 0
    assert batch.statistics.successful + batch.statistics.review_required == 2
    output = tmp_path / "delivery.csv"
    write_delivery_csv(batch, output)
    content = output.read_text(encoding="utf-8")
    assert "FRIGIDAIRE®" in content
    with output.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        records = list(reader)
        assert tuple(reader.fieldnames or ()) == UNILOG_DELIVERY_HEADERS
    assert [record["Mfg_Part_Num"] for record in records] == ["DCB518ASTS06G", "ABC"]
    assert not {"confidenceBp", "reviewRequired", "provenance", "enrichmentId"} & set(records[0])
    assert records[0]["UPC"] == ""
    assert "None" not in content and "null" not in content


class _FailingService(UnilogEnrichmentService):
    def enrich_row(self, input_row, vocabulary=None):  # type: ignore[no-untyped-def]
        if input_row.mfg_part_num == "FAIL":
            raise RuntimeError("isolated")
        return super().enrich_row(input_row, vocabulary)


def test_batch_isolates_row_failure_and_rejects_more_than_one_thousand(
    tmp_path: Path,
) -> None:
    rows = (
        challenge_row(row_id="a" * 64),
        challenge_row(row_id="b" * 64, part="FAIL", description="FAIL Valve"),
        challenge_row(row_id="c" * 64, part="OK", description="OK Valve"),
    )
    batch = UnilogBatchEnrichmentService(_FailingService()).enrich_batch(rows)
    assert [item.status for item in batch.rows] == [
        BatchRowStatus.REVIEW_REQUIRED,
        BatchRowStatus.FAILED,
        BatchRowStatus.REVIEW_REQUIRED,
    ]
    assert batch.statistics.failed == 1
    assert batch.rows[1].enrichment is None
    assert "RuntimeError" in (batch.rows[1].error or "")
    output = tmp_path / "isolated.csv"
    write_delivery_csv(batch, output)
    with output.open(encoding="utf-8", newline="") as stream:
        exported = list(csv.DictReader(stream))
    assert [item["Mfg_Part_Num"] for item in exported] == ["DCB518ASTS06G", "FAIL", "OK"]
    assert exported[1]["Product Name"] == ""
    with pytest.raises(ValueError, match="1000"):
        UnilogBatchEnrichmentService().enrich_batch(
            challenge_row(row_id=f"{index:064x}") for index in range(1_001)
        )


def test_official_labelled_rows_field_regression_when_configured() -> None:
    input_value = os.getenv("UNILOG_CHALLENGE_INPUT_PATH")
    output_value = os.getenv("UNILOG_CHALLENGE_EXPECTED_OUTPUT_PATH")
    if not input_value or not output_value:
        pytest.skip("official challenge artifact paths are not configured")
    imported_at = datetime.now(UTC)
    _, inputs = parse_input_csv(Path(input_value), imported_at=imported_at)
    _, expected = parse_expected_output_csv(Path(output_value), imported_at=imported_at)
    observed = derive_observed_vocabulary(expected)
    by_part = {item.mfg_part_num: item for item in inputs}
    service = UnilogEnrichmentService()
    reports: dict[str, Counter[str]] = {}
    for truth in expected:
        actual = service.enrich_row(by_part[truth.mfg_part_num], observed).delivery_record
        reports[truth.mfg_part_num] = Counter(
            compare_field(
                field,
                str(expected_value) if expected_value is not None else None,
                str(actual.value(field)) if actual.value(field) is not None else None,
            ).status.value
            for field, expected_value in truth.expected.as_dict().items()
        )
    assert reports["PDSH4816AF"]["EXACT_MATCH"] >= 9
    assert reports["WDTS7024RZ"]["EXACT_MATCH"] >= 9
    assert all(report["MISMATCH"] < 10 for report in reports.values())
    # No enrichment API accepts a ground-truth record or row-specific expected mapping.
    assert "expected" not in UnilogEnrichmentService.enrich_row.__code__.co_varnames
