"""Bounded CSV parsers for the two official challenge artifacts."""

import csv
import hashlib
from datetime import datetime
from pathlib import Path

from app.core.exceptions import (
    UnilogChallengeInputNotFoundError,
    UnilogChallengeInputSchemaInvalidError,
    UnilogChallengeOutputNotFoundError,
    UnilogChallengeOutputSchemaInvalidError,
)
from app.domain.unilog_challenge import (
    DatasetMetadata,
    DatasetSplit,
    ManufacturerParseStatus,
    UnilogChallengeInputRow,
    UnilogDeliveryRecord,
    UnilogGroundTruthRecord,
)
from app.domain.unilog_challenge.delivery_schema import UNILOG_DELIVERY_HEADERS
from app.services.unilog_challenge.cleansing import clean_challenge_value
from app.services.unilog_challenge.manufacturer import parse_part_manufacturer

PARSER_VERSION = "unilog-challenge-adapter-v1"
INPUT_HEADERS = (
    "Mfg_Part_Num",
    "Part_Desc",
    "E1_Brand",
    "Unilog_Brand",
    "DIB_Brand",
    "Part_Manuf",
)
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_ROWS = 50_000
MAX_COLUMNS = 300
MAX_CELL_CHARACTERS = 50_000


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_input_csv(
    path: Path, *, imported_at: datetime
) -> tuple[DatasetMetadata, tuple[UnilogChallengeInputRow, ...]]:
    header, raw_rows, fingerprint = _read_csv(
        path,
        missing_error=UnilogChallengeInputNotFoundError,
        schema_error=UnilogChallengeInputSchemaInvalidError,
    )
    if header != INPUT_HEADERS:
        raise UnilogChallengeInputSchemaInvalidError(
            "input headers must match the six official ordered headers"
        )
    rows = []
    for row_number, raw in enumerate(raw_rows, start=2):
        values = dict(zip(header, raw, strict=True))
        part_number = values["Mfg_Part_Num"]
        description = values["Part_Desc"]
        if not part_number or not description:
            raise UnilogChallengeInputSchemaInvalidError(
                f"input row {row_number} is missing a required part number or description"
            )
        parsed = parse_part_manufacturer(values["Part_Manuf"])
        row_identity = hashlib.sha256(
            f"{fingerprint}:{row_number}:{part_number}".encode()
        ).hexdigest()
        rows.append(
            UnilogChallengeInputRow(
                row_id=row_identity,
                source_row_number=row_number,
                mfg_part_num=part_number,
                part_desc=description,
                e1_brand_raw=values["E1_Brand"],
                unilog_brand_raw=values["Unilog_Brand"],
                dib_brand_raw=values["DIB_Brand"],
                part_manuf_raw=values["Part_Manuf"],
                e1_brand_clean=clean_challenge_value(values["E1_Brand"]),
                unilog_brand_clean=clean_challenge_value(values["Unilog_Brand"]),
                dib_brand_clean=clean_challenge_value(values["DIB_Brand"]),
                parsed_manufacturer=parsed.manufacturer_text,
                source_reference_code=parsed.source_reference_code,
                manufacturer_parse_status=parsed.status,
            )
        )
    metadata = DatasetMetadata(
        filename=path.name,
        sha256=fingerprint,
        row_count=len(rows),
        column_count=len(header),
        parser_version=PARSER_VERSION,
        imported_at=imported_at,
    )
    return metadata, tuple(rows)


def parse_expected_output_csv(
    path: Path, *, imported_at: datetime
) -> tuple[DatasetMetadata, tuple[UnilogGroundTruthRecord, ...]]:
    header, raw_rows, fingerprint = _read_csv(
        path,
        missing_error=UnilogChallengeOutputNotFoundError,
        schema_error=UnilogChallengeOutputSchemaInvalidError,
    )
    if header != UNILOG_DELIVERY_HEADERS:
        raise UnilogChallengeOutputSchemaInvalidError(
            "output headers must match all 252 official headers in exact order"
        )
    rows = []
    for row_number, raw in enumerate(raw_rows, start=2):
        values = {
            key: value if value != "" else None for key, value in zip(header, raw, strict=True)
        }
        part_number = values["Mfg_Part_Num"]
        if not isinstance(part_number, str) or not part_number:
            raise UnilogChallengeOutputSchemaInvalidError(
                f"expected-output row {row_number} has no Mfg_Part_Num"
            )
        record = UnilogDeliveryRecord.from_mapping(values)
        populated = frozenset(key for key, value in values.items() if value is not None)
        rows.append(
            UnilogGroundTruthRecord(
                source_output_row_number=row_number,
                mfg_part_num=part_number,
                expected=record,
                populated_fields=populated,
                split=_deterministic_split(part_number),
            )
        )
    metadata = DatasetMetadata(
        filename=path.name,
        sha256=fingerprint,
        row_count=len(rows),
        column_count=len(header),
        parser_version=PARSER_VERSION,
        imported_at=imported_at,
    )
    return metadata, tuple(rows)


def _deterministic_split(part_number: str) -> DatasetSplit:
    bucket = int(hashlib.sha256(part_number.encode()).hexdigest()[:8], 16) % 100
    if bucket < 70:
        return DatasetSplit.TRAIN
    if bucket < 85:
        return DatasetSplit.DEVELOPMENT
    return DatasetSplit.EVALUATION


def _read_csv(
    path: Path,
    *,
    missing_error: type[UnilogChallengeInputNotFoundError]
    | type[UnilogChallengeOutputNotFoundError],
    schema_error: type[UnilogChallengeInputSchemaInvalidError]
    | type[UnilogChallengeOutputSchemaInvalidError],
) -> tuple[tuple[str, ...], list[tuple[str, ...]], str]:
    if not path.is_file():
        raise missing_error()
    if path.suffix.casefold() != ".csv":
        raise schema_error("the supplied challenge artifact must be a CSV file")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise schema_error("challenge CSV exceeds the 20 MiB safety limit")
    fingerprint = file_sha256(path)
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            header = tuple(next(reader))
            if (
                not header
                or len(header) > MAX_COLUMNS
                or any(not item for item in header)
                or len(set(header)) != len(header)
            ):
                raise schema_error("challenge CSV headers are blank, duplicated, or unbounded")
            rows: list[tuple[str, ...]] = []
            for row_number, raw in enumerate(reader, start=2):
                if row_number > MAX_ROWS + 1:
                    raise schema_error("challenge CSV exceeds the row safety limit")
                row = tuple(raw)
                if len(row) != len(header):
                    raise schema_error(f"challenge CSV row {row_number} has the wrong width")
                if any(len(value) > MAX_CELL_CHARACTERS for value in row):
                    raise schema_error(f"challenge CSV row {row_number} contains an oversized cell")
                if any(row):
                    rows.append(row)
    except (UnicodeDecodeError, csv.Error, StopIteration) as exc:
        raise schema_error("challenge CSV is malformed or has no header") from exc
    return header, rows, fingerprint


def parsed_manufacturer_count(rows: tuple[UnilogChallengeInputRow, ...]) -> tuple[int, int]:
    successes = sum(row.manufacturer_parse_status is ManufacturerParseStatus.PARSED for row in rows)
    ambiguous = sum(
        row.manufacturer_parse_status is ManufacturerParseStatus.AMBIGUOUS for row in rows
    )
    return successes, ambiguous
