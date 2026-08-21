"""Semantic attributes, coverage, descriptions, confidence, and review metrics."""

from datetime import UTC, datetime

from app.domain.unilog_challenge import UnilogDeliveryRecord
from app.services.unilog_challenge.batch_enrichment import UnilogBatchEnrichmentService
from app.services.unilog_challenge.enrichment_service import UnilogEnrichmentService
from app.services.unilog_evaluation.attribute_comparator import evaluate_attributes
from app.services.unilog_evaluation.attribute_coverage_evaluator import evaluate_attribute_coverage
from app.services.unilog_evaluation.batch_evaluator import evaluate_batch_quality
from app.services.unilog_evaluation.classification_evaluator import evaluate_classification
from app.services.unilog_evaluation.coverage_evaluator import evaluate_coverage
from app.services.unilog_evaluation.description_compliance import (
    evaluate_description_compliance,
)
from tests.unit.unilog_challenge.helpers import challenge_row


def _record(**values: str) -> UnilogDeliveryRecord:
    mapping = UnilogDeliveryRecord.blank().as_dict()
    mapping.update(values)
    return UnilogDeliveryRecord.from_mapping(mapping)


def test_semantic_attribute_match_is_slot_independent() -> None:
    expected = _record(
        **{
            "ATTRIBUTE_LABEL 13": "Material",
            "ATTRIBUTE_VALUE 13": "Stainless Steel",
        }
    )
    actual = _record(
        **{
            "ATTRIBUTE_LABEL 1": "material",
            "ATTRIBUTE_VALUE 1": "Stainless  Steel",
        }
    )
    metrics = evaluate_attributes(((expected, actual),))
    assert metrics.position_exact_cell_count == 0
    assert metrics.matched_label_count == 1
    assert metrics.matched_value_count == 1
    assert metrics.matched_triple_count == 1
    assert metrics.precision_bp == metrics.recall_bp == metrics.f1_bp == 10_000


def test_attribute_uom_and_undefined_precision_are_reported_honestly() -> None:
    expected = _record(
        **{
            "ATTRIBUTE_LABEL 1": "Voltage Rating",
            "ATTRIBUTE_VALUE 1": "120",
            "ATTRIBUTE_UOM 1": "V",
        }
    )
    metrics = evaluate_attributes(((expected, UnilogDeliveryRecord.blank()),))
    assert metrics.expected_attribute_count == 1
    assert metrics.generated_attribute_count == 0
    assert metrics.precision_bp is None
    assert metrics.recall_bp == 0
    assert metrics.uom_accuracy_bp == 0


def test_batch_metrics_separate_reliability_review_confidence_and_coverage() -> None:
    service = UnilogEnrichmentService(now=lambda: datetime(2026, 8, 21, tzinfo=UTC))
    batch = UnilogBatchEnrichmentService(service).enrich_batch(
        (
            challenge_row(row_id="a" * 64),
            challenge_row(
                row_id="b" * 64,
                part="ABC",
                description="ABC unknown item",
                e1="-- Unbranded --",
                manufacturer="",
            ),
        )
    )
    review, quality = evaluate_batch_quality(batch)
    coverage = evaluate_coverage(batch)
    descriptions = evaluate_description_compliance(batch)
    classification = evaluate_classification(batch)
    attribute_coverage = evaluate_attribute_coverage(batch)
    assert quality.total_rows == quality.processed_rows == 2
    assert classification.total_rows == 2
    assert classification.resolved_product_type_count == 1
    assert classification.product_type_coverage_bp == 5_000
    assert attribute_coverage.total_rows == 2
    assert attribute_coverage.semantic_candidates_extracted > 0
    assert quality.failed_rows == 0
    assert quality.processing_success_rate_bp == 10_000
    assert review.review_required_count == 2
    assert review.review_required_rate_bp == 10_000
    assert sum(item.count for item in review.confidence_bands) == 2
    assert coverage.row_count == 2
    assert coverage.raw_coverage_rate_bp < coverage.supported_coverage_rate_bp
    assert coverage.strategy_coverage
    assert coverage.external_or_unsupported_blank_rate_bp == 10_000
    assert descriptions.invoice_uppercase_compliance_bp == 10_000
    assert descriptions.invoice_max_40_compliance_bp == 10_000
    assert descriptions.grounding_compliance_bp == 10_000
    assert descriptions.unsupported_fact_violation_count == 0
