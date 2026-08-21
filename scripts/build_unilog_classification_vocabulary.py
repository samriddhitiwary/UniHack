"""Build the deterministic SPEC-044 classification artifact from official CSVs."""

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from app.domain.unilog_challenge import UnilogGroundTruthRecord
from app.importers.unilog_challenge.parsers import (
    parse_expected_output_csv,
    parse_input_csv,
)
from app.services.unilog_challenge.ground_truth import (
    align_ground_truth,
    attach_alignments,
)
from app.services.unilog_classification.vocabulary_builder import (
    build_classification_vocabulary,
)
from app.services.unilog_classification.vocabulary_store import (
    write_classification_vocabulary,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Official challenge input CSV")
    parser.add_argument("--ground-truth", help="Optional official labelled output CSV")
    parser.add_argument("--artifact", required=True, help="Destination JSON artifact")
    args = parser.parse_args()
    imported_at = datetime.now(UTC)
    input_metadata, rows = parse_input_csv(Path(args.input), imported_at=imported_at)
    truths: tuple[UnilogGroundTruthRecord, ...] = ()
    if args.ground_truth:
        _, parsed_truths = parse_expected_output_csv(
            Path(args.ground_truth), imported_at=imported_at
        )
        truths = attach_alignments(
            parsed_truths, align_ground_truth(rows, parsed_truths)
        )
    vocabulary = build_classification_vocabulary(
        rows, input_sha256=input_metadata.sha256, ground_truth_rows=truths
    )
    write_classification_vocabulary(vocabulary, Path(args.artifact))
    print(
        json.dumps(
            {
                "vocabularyHash": vocabulary.vocabulary_hash,
                **asdict(vocabulary.statistics),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
