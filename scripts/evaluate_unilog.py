"""Run post-enrichment Unilog evaluation and write a deterministic JSON report."""

import argparse
import json
from pathlib import Path

from app.repositories.in_memory_unilog_evaluation import (
    InMemoryUnilogEvaluationRepository,
)
from app.services.unilog_evaluation.evaluation_service import UnilogEvaluationService
from app.services.unilog_evaluation.serialization import (
    serialize_evaluation_summary,
    serialize_labelled_row,
    serialize_value,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", required=True, type=Path, help="Official challenge input CSV"
    )
    parser.add_argument(
        "--ground-truth",
        required=True,
        type=Path,
        help="Official labelled delivery CSV",
    )
    parser.add_argument(
        "--report", required=True, type=Path, help="JSON report destination"
    )
    args = parser.parse_args()
    result = UnilogEvaluationService(
        InMemoryUnilogEvaluationRepository()
    ).create_from_paths(args.input, args.ground_truth)
    report = serialize_evaluation_summary(result)
    report.pop("createdAt", None)
    report["fieldMetrics"] = serialize_value(result.field_metrics)
    report["labelledRows"] = [
        serialize_labelled_row(row) for row in result.labelled_rows
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    metrics = result.accuracy
    batch = result.batch_metrics
    attributes = result.attribute_coverage_metrics
    print(f"Labelled rows: {result.labelled_row_count}")
    print(f"Exact matches: {metrics.exact_match_count}")
    print(f"Normalized matches: {metrics.normalized_match_count}")
    print(f"Mismatches: {metrics.mismatch_count}")
    print(f"Expected values missing: {metrics.expected_populated_actual_blank_count}")
    print(f"Batch rows: {batch.total_rows}")
    print(f"Processed: {batch.processed_rows}")
    print(f"Review required: {batch.review_required_rows}")
    print(f"Failed: {batch.failed_rows}")
    print(f"Semantic attribute candidates: {attributes.semantic_candidates_extracted}")
    print(f"Official attributes resolved: {attributes.official_attributes_resolved}")
    print(f"Products with attributes: {attributes.products_with_attributes}")
    print(
        "Average official attributes/product: "
        f"{attributes.average_attributes_per_product_bp / 100:.2f}"
    )
    print(f"Unknown semantic labels: {attributes.unknown_semantic_labels}")
    print(f"Attribute conflicts: {attributes.conflicts}")
    print(f"Attribute unit ambiguities: {attributes.unit_ambiguities}")
    print(f"Attribute overflow: {attributes.overflow_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
