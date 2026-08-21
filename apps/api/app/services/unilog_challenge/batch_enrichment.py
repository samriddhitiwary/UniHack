"""Bounded, order-preserving, row-isolated batch enrichment and exact CSV export."""

import csv
from collections.abc import Iterable
from pathlib import Path

from app.domain.unilog_challenge import (
    MAX_UNILOG_BATCH_ROWS,
    BatchRowStatus,
    ObservedVocabulary,
    UnilogBatchEnrichmentResult,
    UnilogBatchRowResult,
    UnilogBatchStatistics,
    UnilogChallengeInputRow,
)
from app.domain.unilog_challenge.delivery_schema import UNILOG_DELIVERY_HEADERS
from app.services.unilog_challenge.enrichment_service import UnilogEnrichmentService


class UnilogBatchEnrichmentService:
    def __init__(self, enrichment: UnilogEnrichmentService | None = None) -> None:
        self._enrichment = enrichment or UnilogEnrichmentService()

    def enrich_batch(
        self,
        rows: Iterable[UnilogChallengeInputRow],
        vocabulary: ObservedVocabulary | None = None,
    ) -> UnilogBatchEnrichmentResult:
        materialized = tuple(rows)
        if len(materialized) > MAX_UNILOG_BATCH_ROWS:
            raise ValueError("Unilog enrichment batch cannot exceed 1000 rows")
        results: list[UnilogBatchRowResult] = []
        for row in materialized:
            try:
                enrichment = self._enrichment.enrich_row(row, vocabulary)
                status = (
                    BatchRowStatus.REVIEW_REQUIRED
                    if enrichment.review_required
                    else BatchRowStatus.SUCCESS
                )
                results.append(
                    UnilogBatchRowResult(
                        input_row_id=row.row_id,
                        input_row=row,
                        status=status,
                        enrichment=enrichment,
                        error=None,
                    )
                )
            except Exception as exc:  # row isolation boundary; details remain internal
                results.append(
                    UnilogBatchRowResult(
                        input_row_id=row.row_id,
                        input_row=row,
                        status=BatchRowStatus.FAILED,
                        enrichment=None,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
        completed = [item.enrichment for item in results if item.enrichment is not None]
        total_completed = len(completed)
        statistics = UnilogBatchStatistics(
            total=len(results),
            successful=sum(item.status is BatchRowStatus.SUCCESS for item in results),
            review_required=sum(item.status is BatchRowStatus.REVIEW_REQUIRED for item in results),
            failed=sum(item.status is BatchRowStatus.FAILED for item in results),
            average_populated_fields=(
                sum(item.populated_field_count for item in completed) // total_completed
                if completed
                else 0
            ),
            average_confidence_bp=(
                sum(item.overall_confidence_bp for item in completed) // total_completed
                if completed
                else 0
            ),
        )
        return UnilogBatchEnrichmentResult(rows=tuple(results), statistics=statistics)


def write_delivery_csv(batch: UnilogBatchEnrichmentResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=UNILOG_DELIVERY_HEADERS,
            extrasaction="raise",
            lineterminator="\n",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        for item in batch.rows:
            values = (
                item.enrichment.delivery_record.as_dict()
                if item.enrichment is not None
                else _failed_row_values(item.input_row)
            )
            writer.writerow({key: "" if value is None else value for key, value in values.items()})


def _failed_row_values(row: UnilogChallengeInputRow) -> dict[str, str | None]:
    values: dict[str, str | None] = {header: None for header in UNILOG_DELIVERY_HEADERS}
    values.update(
        {
            "Mfg_Part_Num": row.mfg_part_num,
            "Part_Desc": row.part_desc,
            "E1_Brand": row.e1_brand_raw,
            "Unilog_Brand": row.unilog_brand_raw,
            "DIB_Brand": row.dib_brand_raw,
            "Part_Manuf": row.part_manuf_raw,
            "MANUFACTURER_PART_NUMBER": row.mfg_part_num,
        }
    )
    return values
