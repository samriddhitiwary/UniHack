"""Coverage and labelled accuracy metrics for independent identity resolution."""

from collections import Counter

from app.domain.unilog_challenge import UnilogBatchEnrichmentResult, UnilogDeliveryRecord
from app.domain.unilog_evaluation import UnilogIdentityResolutionMetrics


def evaluate_identity_resolution(
    batch: UnilogBatchEnrichmentResult,
    labelled_pairs: tuple[tuple[UnilogDeliveryRecord, UnilogDeliveryRecord], ...],
) -> UnilogIdentityResolutionMetrics:
    completed = tuple(item.enrichment for item in batch.rows if item.enrichment is not None)
    total = len(batch.rows)
    manufacturer_resolved = sum(
        item.delivery_record.value("MANUFACTURER_NAME") not in (None, "") for item in completed
    )
    brand_resolved = sum(
        item.delivery_record.value("BRAND_NAME") not in (None, "") for item in completed
    )
    reasons: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    for item in completed:
        row_reasons = {
            warning.removeprefix("IDENTITY:")
            for warning in item.warnings
            if warning.startswith("IDENTITY:")
        }
        reasons.update(row_reasons)
        for resolution in item.field_resolutions:
            if (
                resolution.field_name not in {"MANUFACTURER_NAME", "BRAND_NAME"}
                or not resolution.provenance
            ):
                continue
            reference = resolution.provenance.source_reference
            source = (
                "ORGANIZER_BRAND_FIELDS"
                if "_BRAND:" in reference
                else "DESCRIPTION_EVIDENCE"
                if "PART_DESC:" in reference
                else "MPN_PREFIX_EVIDENCE"
                if "MPN_PREFIX:" in reference
                else "REPEATED_DATASET_PATTERN"
                if "DATASET_RELATION:" in reference
                else "PART_MANUF"
            )
            sources[source] += 1
    manufacturer_exact = sum(
        expected.value("MANUFACTURER_NAME") == actual.value("MANUFACTURER_NAME")
        and expected.value("MANUFACTURER_NAME") not in (None, "")
        for expected, actual in labelled_pairs
    )
    brand_exact = sum(
        expected.value("BRAND_NAME") == actual.value("BRAND_NAME")
        and expected.value("BRAND_NAME") not in (None, "")
        for expected, actual in labelled_pairs
    )
    return UnilogIdentityResolutionMetrics(
        total_rows=total,
        manufacturer_resolved=manufacturer_resolved,
        manufacturer_resolution_coverage_bp=(
            manufacturer_resolved * 10_000 // total if total else 0
        ),
        manufacturer_ambiguous=reasons["MANUFACTURER_AMBIGUOUS"],
        brand_resolved=brand_resolved,
        brand_resolution_coverage_bp=brand_resolved * 10_000 // total if total else 0,
        brand_ambiguous=reasons["BRAND_AMBIGUOUS"],
        supplier_only_rows=reasons["SUPPLIER_ONLY_EVIDENCE"],
        manufacturer_exact_labelled=manufacturer_exact,
        brand_exact_labelled=brand_exact,
        labelled_rows=len(labelled_pairs),
        review_reason_counts=tuple(sorted(reasons.items())),
        evidence_source_counts=tuple(sorted(sources.items())),
    )
