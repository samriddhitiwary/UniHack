"""Create an exact-schema Unilog delivery CSV from the official challenge input."""

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from app.importers.unilog_challenge.parsers import (
    parse_expected_output_csv,
    parse_input_csv,
)
from app.services.unilog_challenge.batch_enrichment import (
    UnilogBatchEnrichmentService,
    write_delivery_csv,
)
from app.services.unilog_challenge.ground_truth import derive_observed_vocabulary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", required=True, type=Path, help="Official six-column input CSV"
    )
    parser.add_argument(
        "--output", required=True, type=Path, help="Delivery CSV destination"
    )
    parser.add_argument(
        "--labelled-output",
        type=Path,
        help="Optional official labelled CSV used only for general observed vocabulary",
    )
    args = parser.parse_args()
    imported_at = datetime.now(UTC)
    _, rows = parse_input_csv(args.input, imported_at=imported_at)
    vocabulary = None
    if args.labelled_output is not None:
        _, labelled = parse_expected_output_csv(
            args.labelled_output, imported_at=imported_at
        )
        vocabulary = derive_observed_vocabulary(labelled)
    batch = UnilogBatchEnrichmentService().enrich_batch(rows, vocabulary)
    write_delivery_csv(batch, args.output)
    print(
        json.dumps(
            {
                "rowsProcessed": batch.statistics.total,
                "rowsEnriched": (
                    batch.statistics.successful + batch.statistics.review_required
                ),
                "rowsReviewRequired": batch.statistics.review_required,
                "rowsFailed": batch.statistics.failed,
                "outputPath": str(args.output.resolve()),
                "policyVersion": "unilog-enrichment-policy-v1",
                "statistics": asdict(batch.statistics),
            }
        )
    )
    return 0 if batch.statistics.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
