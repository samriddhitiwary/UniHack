"""Aggregate metrics, deterministic identities, errors, and persistence."""

from datetime import UTC, datetime

import pytest

from app.domain.unilog_challenge import (
    DatasetSplit,
    UnilogDeliveryRecord,
    UnilogGroundTruthRecord,
)
from app.repositories.in_memory_unilog_evaluation import InMemoryUnilogEvaluationRepository
from app.services.unilog_challenge.batch_enrichment import UnilogBatchEnrichmentService
from app.services.unilog_evaluation.evaluation_service import UnilogEvaluationService
from tests.unit.unilog_challenge.helpers import challenge_row

_NOW = datetime(2026, 8, 21, 12, tzinfo=UTC)


def _truth(row_id: str) -> UnilogGroundTruthRecord:
    values = UnilogDeliveryRecord.blank().as_dict()
    values.update(
        {
            "Mfg_Part_Num": "ABC",
            "Part_Desc": "ABC Valve",
            "MANUFACTURER_PART_NUMBER": "ABC",
            "Product Name": "Valve",
            "BRAND_NAME": "Acme®",
        }
    )
    record = UnilogDeliveryRecord.from_mapping(values)
    return UnilogGroundTruthRecord(
        source_output_row_number=2,
        mfg_part_num="ABC",
        expected=record,
        populated_fields=frozenset(key for key, value in values.items() if value is not None),
        split=DatasetSplit.TRAIN,
        input_row_id=row_id,
    )


def test_evaluation_is_deterministic_and_persisted_separately() -> None:
    row = challenge_row(
        row_id="a" * 64,
        part="ABC",
        description="ABC Valve",
        e1="-- Unbranded --",
        manufacturer="",
    )
    batch = UnilogBatchEnrichmentService().enrich_batch((row,))
    repository = InMemoryUnilogEvaluationRepository()
    service = UnilogEvaluationService(repository, now=lambda: _NOW)
    first = service.evaluate(batch, (_truth(row.row_id),), dataset_fingerprint="d" * 64)
    second = service.evaluate(batch, (_truth(row.row_id),), dataset_fingerprint="d" * 64)
    assert first.evaluation_id == second.evaluation_id
    assert first.accuracy.exact_match_count == 4
    assert first.accuracy.expected_populated_actual_blank_count == 1
    assert first.accuracy.both_blank_count == 238
    assert first.accuracy.evaluable_field_count == 5
    assert first.batch_metrics.processing_success_rate_bp == 10_000
    assert first.problems
    assert first.recommendations
    repository.save(first)
    assert service.get(first.evaluation_id) == first
    assert service.latest() == first


def test_evaluation_rejects_unaligned_or_missing_generated_truth() -> None:
    batch = UnilogBatchEnrichmentService().enrich_batch((challenge_row(),))
    truth = _truth("b" * 64)
    with pytest.raises(ValueError, match="uniquely aligned"):
        UnilogEvaluationService(InMemoryUnilogEvaluationRepository()).evaluate(
            batch, (truth,), dataset_fingerprint="d" * 64
        )
