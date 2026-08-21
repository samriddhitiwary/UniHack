"""Unlabelled attribute coverage, frequency, and review metrics."""

from collections import Counter

from app.domain.unilog_attributes import AttributeReviewReason
from app.domain.unilog_challenge import UnilogBatchEnrichmentResult
from app.domain.unilog_evaluation import (
    UnilogAttributeCoverageMetrics,
    UnilogAttributeLabelFrequency,
)


def evaluate_attribute_coverage(
    batch: UnilogBatchEnrichmentResult,
) -> UnilogAttributeCoverageMetrics:
    enrichments = tuple(row.enrichment for row in batch.rows if row.enrichment is not None)
    official_by_row = tuple(
        tuple(
            item
            for item in enrichment.attributes
            if item.official_label is not None and not item.review_required
        )
        for enrichment in enrichments
    )
    all_candidates = tuple(item for enrichment in enrichments for item in enrichment.attributes)
    labels = Counter(
        item.official_label for items in official_by_row for item in items if item.official_label
    )
    reasons = Counter(reason.value for item in all_candidates for reason in item.review_reasons)
    total_rows = len(batch.rows)
    official_count = sum(len(items) for items in official_by_row)
    return UnilogAttributeCoverageMetrics(
        total_rows=total_rows,
        products_with_attributes=sum(bool(items) for items in official_by_row),
        attribute_coverage_bp=(
            sum(bool(items) for items in official_by_row) * 10_000 // total_rows
            if total_rows
            else 0
        ),
        official_attributes_resolved=official_count,
        average_attributes_per_product_bp=(official_count * 100 // total_rows if total_rows else 0),
        semantic_candidates_extracted=len(all_candidates),
        unknown_semantic_labels=sum(item.official_label is None for item in all_candidates),
        conflicts=reasons[AttributeReviewReason.ATTRIBUTE_CONFLICT.value],
        unit_ambiguities=reasons[AttributeReviewReason.ATTRIBUTE_UNIT_AMBIGUOUS.value],
        overflow_count=reasons[AttributeReviewReason.ATTRIBUTE_OVERFLOW.value],
        review_reason_counts=tuple(sorted(reasons.items(), key=lambda item: (-item[1], item[0]))),
        top_attribute_labels=tuple(
            UnilogAttributeLabelFrequency(label=label, count=count)
            for label, count in sorted(labels.items(), key=lambda item: (-item[1], item[0]))[:10]
        ),
    )
