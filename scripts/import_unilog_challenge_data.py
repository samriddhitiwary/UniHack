"""Import official Unilog challenge CSVs into a deterministic local artifact."""

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from app.importers.unilog_challenge import (
    import_unilog_challenge_data,
    write_import_artifact,
)


def _configured_path(argument: str | None, environment_name: str) -> Path | None:
    value = argument or os.getenv(environment_name)
    return Path(value).expanduser() if value else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="Official challenge input CSV")
    parser.add_argument("--expected-output", help="Official expected-output CSV")
    parser.add_argument("--artifact", help="Destination JSON artifact")
    args = parser.parse_args()
    input_path = _configured_path(args.input, "UNILOG_CHALLENGE_INPUT_PATH")
    output_path = _configured_path(
        args.expected_output, "UNILOG_CHALLENGE_EXPECTED_OUTPUT_PATH"
    )
    artifact_path = _configured_path(args.artifact, "UNILOG_CHALLENGE_ARTIFACT_PATH")
    if input_path is None or output_path is None or artifact_path is None:
        parser.error(
            "provide --input, --expected-output, and --artifact or their UNILOG_CHALLENGE_* environment values"
        )
    imported = import_unilog_challenge_data(input_path, output_path)
    write_import_artifact(imported, artifact_path)
    print(json.dumps({"importId": imported.import_id, **asdict(imported.statistics)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
