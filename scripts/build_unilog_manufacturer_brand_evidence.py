"""Build the deterministic SPEC-046 manufacturer and brand evidence artifact."""

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from app.importers.unilog_challenge.parsers import (
    parse_expected_output_csv,
    parse_input_csv,
)
from app.services.unilog_challenge.ground_truth import (
    align_ground_truth,
    attach_alignments,
)
from app.services.unilog_identity.vocabulary_builder import (
    build_manufacturer_brand_evidence,
)
from app.services.unilog_identity.vocabulary_store import write_identity_artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--ground-truth", required=True, type=Path)
    parser.add_argument("--artifact", required=True, type=Path)
    args = parser.parse_args()
    imported_at = datetime.now(UTC)
    input_metadata, rows = parse_input_csv(args.input, imported_at=imported_at)
    truth_metadata, raw_truths = parse_expected_output_csv(
        args.ground_truth, imported_at=imported_at
    )
    truths = attach_alignments(raw_truths, align_ground_truth(rows, raw_truths))
    artifact = build_manufacturer_brand_evidence(
        rows,
        input_sha256=input_metadata.sha256,
        ground_truth_sha256=truth_metadata.sha256,
        ground_truth_rows=truths,
    )
    write_identity_artifact(artifact, args.artifact)
    print(
        json.dumps(
            {"artifactHash": artifact.artifact_hash, **asdict(artifact.statistics)}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
