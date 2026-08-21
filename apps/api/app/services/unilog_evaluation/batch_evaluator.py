"""Review, confidence-band, and processing-reliability analytics."""

from collections import Counter
from statistics import median_low

from app.domain.unilog_challenge import BatchRowStatus, UnilogBatchEnrichmentResult
from app.domain.unilog_evaluation import (
    ConfidenceBand,
    UnilogBatchQualityMetrics,
    UnilogConfidenceBandMetric,
    UnilogReviewMetrics,
)


def evaluate_batch_quality(
    batch: UnilogBatchEnrichmentResult,
) -> tuple[UnilogReviewMetrics, UnilogBatchQualityMetrics]:
    total = len(batch.rows)
    completed = tuple(item.enrichment for item in batch.rows if item.enrichment is not None)
    failed = sum(item.status is BatchRowStatus.FAILED for item in batch.rows)
    review = sum(item.status is BatchRowStatus.REVIEW_REQUIRED for item in batch.rows)
    confidences = [item.overall_confidence_bp for item in completed]
    bands = Counter(_band(value) for value in confidences)
    reasons: Counter[str] = Counter()
    for enrichment in completed:
        row_reasons: set[str] = set()
        identity_reasons = {
            warning.removeprefix("IDENTITY:")
            for warning in enrichment.warnings
            if warning.startswith("IDENTITY:")
        }
        row_reasons.update(_identity_reason_name(reason) for reason in identity_reasons)
        for warning in enrichment.warnings:
            if warning == "MANUFACTURER_REVIEW_REQUIRED" and not identity_reasons:
                row_reasons.add("manufacturerAmbiguity")
            elif warning == "BRAND_REVIEW_REQUIRED" and not identity_reasons:
                row_reasons.add("brandAmbiguity")
            elif warning == "CLASSIFICATION_REVIEW_REQUIRED":
                row_reasons.add("classificationUncertainty")
            elif warning == "ATTRIBUTE_CONFLICT_REVIEW_REQUIRED":
                row_reasons.add("attributeConflict")
            elif warning.startswith("FORMAT_WARNING"):
                row_reasons.add("descriptionWarning")
        if any(
            resolution.value is not None and resolution.confidence_bp < 7_000
            for resolution in enrichment.field_resolutions
        ):
            row_reasons.add("lowConfidenceField")
        reasons.update(row_reasons)
    band_metrics = tuple(
        UnilogConfidenceBandMetric(
            band=band,
            count=bands[band],
            rate_bp=bands[band] * 10_000 // len(confidences) if confidences else 0,
        )
        for band in ConfidenceBand
    )
    return (
        UnilogReviewMetrics(
            review_required_count=review,
            review_required_rate_bp=review * 10_000 // total if total else 0,
            reason_counts=tuple(sorted(reasons.items())),
            average_confidence_bp=(sum(confidences) // len(confidences) if confidences else 0),
            median_confidence_bp=median_low(confidences) if confidences else 0,
            confidence_bands=band_metrics,
        ),
        UnilogBatchQualityMetrics(
            total_rows=total,
            processed_rows=total - failed,
            review_required_rows=review,
            failed_rows=failed,
            processing_success_rate_bp=(total - failed) * 10_000 // total if total else 0,
            failure_rate_bp=failed * 10_000 // total if total else 0,
        ),
    )


def _identity_reason_name(value: str) -> str:
    words = value.casefold().split("_")
    return words[0] + "".join(word.title() for word in words[1:])


def _band(confidence_bp: int) -> ConfidenceBand:
    if confidence_bp >= 9_000:
        return ConfidenceBand.HIGH
    if confidence_bp >= 7_000:
        return ConfidenceBand.MEDIUM
    return ConfidenceBand.LOW
