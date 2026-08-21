"""Compose, profile, and serialize deterministic challenge imports."""

import hashlib
import json
import logging
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.domain.unilog_challenge import (
    AlignmentStatus,
    ImportStatistics,
    UnilogChallengeImport,
)
from app.importers.unilog_challenge.parsers import (
    PARSER_VERSION,
    parse_expected_output_csv,
    parse_input_csv,
    parsed_manufacturer_count,
)
from app.services.unilog_challenge.cleansing import is_challenge_placeholder
from app.services.unilog_challenge.ground_truth import (
    align_ground_truth,
    attach_alignments,
    derive_observed_vocabulary,
)

logger = logging.getLogger(__name__)


def import_unilog_challenge_data(
    input_path: Path,
    expected_output_path: Path,
    *,
    imported_at: datetime | None = None,
) -> UnilogChallengeImport:
    started = imported_at or datetime.now(UTC)
    logger.info("unilog_challenge.import_started")
    input_metadata, input_rows = parse_input_csv(input_path, imported_at=started)
    output_metadata, output_rows = parse_expected_output_csv(
        expected_output_path, imported_at=started
    )
    alignments = align_ground_truth(input_rows, output_rows)
    output_rows = attach_alignments(output_rows, alignments)
    counts = Counter(row.mfg_part_num for row in input_rows)
    placeholders = sum(
        is_challenge_placeholder(value)
        for row in input_rows
        for value in (row.e1_brand_raw, row.unilog_brand_raw, row.dib_brand_raw)
    )
    parse_successes, parse_ambiguous = parsed_manufacturer_count(input_rows)
    statistics = ImportStatistics(
        input_rows=len(input_rows),
        expected_output_rows=len(output_rows),
        input_columns=input_metadata.column_count,
        expected_output_columns=output_metadata.column_count,
        aligned_rows=sum(item.status is AlignmentStatus.ALIGNED for item in alignments),
        unaligned_rows=sum(item.status is AlignmentStatus.NOT_FOUND for item in alignments),
        ambiguous_rows=sum(
            item.status is AlignmentStatus.AMBIGUOUS_ALIGNMENT for item in alignments
        ),
        duplicate_input_keys=sum(value > 1 for value in counts.values()),
        placeholder_values=placeholders,
        manufacturer_parse_successes=parse_successes,
        manufacturer_parse_ambiguous=parse_ambiguous,
    )
    import_id = hashlib.sha256(
        f"{input_metadata.sha256}:{output_metadata.sha256}:{PARSER_VERSION}".encode()
    ).hexdigest()
    result = UnilogChallengeImport(
        import_id=import_id,
        input_metadata=input_metadata,
        output_metadata=output_metadata,
        input_rows=input_rows,
        ground_truth_rows=output_rows,
        alignments=alignments,
        observed_vocabulary=derive_observed_vocabulary(output_rows),
        statistics=statistics,
    )
    logger.info(
        "unilog_challenge.import_completed",
        extra={
            "import_id": import_id,
            "input_rows": statistics.input_rows,
            "expected_output_rows": statistics.expected_output_rows,
            "aligned_rows": statistics.aligned_rows,
            "ambiguous_rows": statistics.ambiguous_rows,
            "input_sha256": input_metadata.sha256,
            "output_sha256": output_metadata.sha256,
        },
    )
    return result


def write_import_artifact(result: UnilogChallengeImport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(_artifact_payload(result), ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def _artifact_payload(result: UnilogChallengeImport) -> dict[str, Any]:
    return {
        "importId": result.import_id,
        "parserVersion": PARSER_VERSION,
        "inputMetadata": _jsonable(asdict(result.input_metadata)),
        "outputMetadata": _jsonable(asdict(result.output_metadata)),
        "statistics": _jsonable(asdict(result.statistics)),
        "inputRows": [_jsonable(asdict(row)) for row in result.input_rows],
        "groundTruthRows": [
            {
                "sourceOutputRowNumber": row.source_output_row_number,
                "mfgPartNum": row.mfg_part_num,
                "inputRowId": row.input_row_id,
                "split": row.split.value,
                "populatedFields": sorted(row.populated_fields),
                "expected": row.expected.as_dict(),
            }
            for row in result.ground_truth_rows
        ],
        "alignments": [_jsonable(asdict(item)) for item in result.alignments],
        "observedVocabulary": {
            "manufacturers": sorted(result.observed_vocabulary.manufacturers),
            "brands": sorted(result.observed_vocabulary.brands),
            "classpaths": sorted(result.observed_vocabulary.classpaths),
            "attributeLabels": sorted(result.observed_vocabulary.attribute_labels),
            "uoms": sorted(result.observed_vocabulary.uoms),
        },
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_jsonable(item) for item in value]
    return value
