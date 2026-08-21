"""Batch classification coverage and review metrics."""

from collections import Counter

from app.domain.unilog_challenge import UnilogBatchEnrichmentResult
from app.domain.unilog_evaluation import UnilogClassificationMetrics, UnilogProductTypeFrequency


def evaluate_classification(batch: UnilogBatchEnrichmentResult) -> UnilogClassificationMetrics:
    classifications = tuple(
        row.enrichment.classification for row in batch.rows if row.enrichment is not None
    )
    total = len(batch.rows)
    resolved = sum(item.product_type_candidate is not None for item in classifications)
    verified = sum(item.classpath is not None for item in classifications)
    review = sum(item.review_required for item in classifications)
    reasons = Counter(reason.value for item in classifications for reason in item.review_reasons)
    types = Counter(
        item.product_type_candidate
        for item in classifications
        if item.product_type_candidate is not None
    )
    top = tuple(
        UnilogProductTypeFrequency(product_type=name, count=count)
        for name, count in sorted(types.items(), key=lambda item: (-item[1], item[0]))[:10]
    )
    return UnilogClassificationMetrics(
        total_rows=total,
        resolved_product_type_count=resolved,
        unresolved_product_type_count=total - resolved,
        product_type_coverage_bp=resolved * 10_000 // total if total else 0,
        verified_classpath_count=verified,
        verified_classpath_coverage_bp=verified * 10_000 // total if total else 0,
        review_required_count=review,
        review_required_rate_bp=review * 10_000 // total if total else 0,
        reason_counts=tuple(sorted(reasons.items(), key=lambda item: (-item[1], item[0]))),
        top_product_types=top,
    )
