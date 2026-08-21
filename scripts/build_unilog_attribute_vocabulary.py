"""Build the deterministic SPEC-045 observed attribute artifact."""

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from app.importers.unilog_challenge.parsers import (
    parse_expected_output_csv,
    parse_input_csv,
)
from app.services.unilog_attributes.vocabulary_builder import build_attribute_vocabulary
from app.services.unilog_attributes.vocabulary_store import write_attribute_vocabulary
from app.services.unilog_challenge.ground_truth import (
    align_ground_truth,
    attach_alignments,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--ground-truth", required=True, type=Path)
    parser.add_argument("--artifact", required=True, type=Path)
    args = parser.parse_args()
    now = datetime.now(UTC)
    input_metadata, rows = parse_input_csv(args.input, imported_at=now)
    output_metadata, raw_truths = parse_expected_output_csv(
        args.ground_truth, imported_at=now
    )
    truths = attach_alignments(raw_truths, align_ground_truth(rows, raw_truths))
    result = build_attribute_vocabulary(
        rows,
        truths,
        input_sha256=input_metadata.sha256,
        ground_truth_sha256=output_metadata.sha256,
    )
    write_attribute_vocabulary(result, args.artifact)
    print(
        json.dumps({"artifactHash": result.artifact_hash, **asdict(result.statistics)})
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
