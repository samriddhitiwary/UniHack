"""Bounded product evidence aggregation for structured attribute candidates."""

from uuid import UUID

from app.core.exceptions import StructuredAttributeExtractionLimitExceededError
from app.domain.attribute_extraction import (
    AttributeExtractionEvidence,
    AttributeExtractionEvidenceType,
)
from app.domain.processing_jobs import ProcessingJob, ProcessingJobStatus, ProcessingJobType
from app.domain.product_sources import ProductSource, ProductSourceType
from app.repositories.csv_processing import CsvProcessingResultRepository
from app.repositories.image_ocr import ImageOcrResultRepository
from app.repositories.pdf_extraction import PdfExtractionResultRepository
from app.repositories.pdf_table_extraction import PdfTableExtractionRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_sources import ProductSourceRepository


class StructuredAttributeEvidenceAggregator:
    def __init__(
        self,
        *,
        source_repository: ProductSourceRepository,
        job_repository: ProcessingJobRepository,
        pdf_text_repository: PdfExtractionResultRepository,
        pdf_table_repository: PdfTableExtractionRepository,
        csv_repository: CsvProcessingResultRepository,
        image_ocr_repository: ImageOcrResultRepository,
        max_items: int = 10_000,
        max_total_characters: int = 1_000_000,
        max_item_characters: int = 10_000,
    ) -> None:
        if min(max_items, max_total_characters, max_item_characters) < 1:
            raise ValueError("attribute evidence limits must be positive")
        self._sources, self._jobs = source_repository, job_repository
        self._pdf_text, self._pdf_tables = pdf_text_repository, pdf_table_repository
        self._csv, self._ocr = csv_repository, image_ocr_repository
        self._max_items, self._max_total, self._max_item = (
            max_items,
            max_total_characters,
            max_item_characters,
        )

    def collect(
        self, product_id: UUID
    ) -> tuple[tuple[AttributeExtractionEvidence, ...], tuple[str, ...]]:
        sources: list[ProductSource] = []
        cursor: str | None = None
        while True:
            page = self._sources.list_by_product(product_id, limit=100, cursor=cursor)
            sources.extend(page.items)
            cursor = page.next_cursor
            if cursor is None:
                break
        items: list[AttributeExtractionEvidence] = []
        warnings: list[str] = []
        total = 0

        def add(
            source_id: UUID,
            kind: AttributeExtractionEvidenceType,
            text: str,
            location: str,
            quality: int,
            label: str | None = None,
            value: str | None = None,
        ) -> None:
            nonlocal total
            normalized = text.replace("\x00", "").strip()
            if not normalized:
                return
            if (
                len(normalized) > self._max_item
                or len(items) >= self._max_items
                or total + len(normalized) > self._max_total
            ):
                raise StructuredAttributeExtractionLimitExceededError()
            items.append(
                AttributeExtractionEvidence(
                    evidence_id=f"evidence-{len(items) + 1:06d}",
                    source_id=source_id,
                    evidence_type=kind,
                    text=normalized,
                    location=location,
                    source_quality_bp=quality,
                    order=len(items),
                    label_hint=label,
                    value_hint=value,
                )
            )
            total += len(normalized)

        for source in sources:
            if source.source_type is ProductSourceType.TEXT:
                for line_number, line in enumerate((source.text_content or "").splitlines(), 1):
                    add(
                        source.source_id,
                        AttributeExtractionEvidenceType.DIRECT_TEXT,
                        line,
                        f"sourceId={source.source_id};lineNumber={line_number}",
                        9_000,
                    )
                continue
            jobs = self._completed(source.product_id, source.source_id)
            if source.source_type is ProductSourceType.PDF:
                job = jobs.get(ProcessingJobType.PDF_TEXT_EXTRACTION)
                text_result = self._pdf_text.get_by_job_id(job.job_id) if job else None
                if text_result:
                    for pdf_page in text_result.pages:
                        for line_number, line in enumerate(pdf_page.text.splitlines(), 1):
                            add(
                                source.source_id,
                                AttributeExtractionEvidenceType.PDF_TEXT,
                                line,
                                f"pageNumber={pdf_page.page_number};lineNumber={line_number}",
                                8_500,
                            )
                job = jobs.get(ProcessingJobType.PDF_TABLE_EXTRACTION)
                table_result = self._pdf_tables.get_by_job_id(job.job_id) if job else None
                if table_result:
                    for table in table_result.tables:
                        for row in table.rows:
                            nonempty = [cell for cell in row.cells if cell.text]
                            location = (
                                f"pageNumber={table.page_number};"
                                f"tableIndex={table.table_index};rowIndex={row.row_index}"
                            )
                            if len(nonempty) >= 2:
                                text = " | ".join(cell.text for cell in nonempty)
                                add(
                                    source.source_id,
                                    AttributeExtractionEvidenceType.PDF_TABLE_ROW,
                                    text,
                                    location,
                                    9_500,
                                    nonempty[0].text,
                                    " ".join(cell.text for cell in nonempty[1:]),
                                )
                            elif nonempty:
                                add(
                                    source.source_id,
                                    AttributeExtractionEvidenceType.PDF_TABLE_CELL,
                                    nonempty[0].text,
                                    location + f";columnIndex={nonempty[0].column_index}",
                                    9_500,
                                )
            elif source.source_type is ProductSourceType.CSV:
                job = jobs.get(ProcessingJobType.CSV_PROCESSING)
                csv_result = self._csv.get_by_job_id(job.job_id) if job else None
                if csv_result and csv_result.row_count == 1:
                    csv_row = csv_result.rows[0]
                    for header, cell in zip(csv_result.header, csv_row.cells, strict=True):
                        add(
                            source.source_id,
                            AttributeExtractionEvidenceType.CSV_CELL,
                            f"{header.text}: {cell.text}",
                            f"rowNumber=1;columnIndex={cell.column_index};headerName={header.text}"[
                                :500
                            ],
                            9_500,
                            header.text,
                            cell.text or None,
                        )
                elif (
                    csv_result
                    and csv_result.row_count > 1
                    and "MULTI_ROW_CSV_SKIPPED" not in warnings
                ):
                    warnings.append("MULTI_ROW_CSV_SKIPPED")
            elif source.source_type is ProductSourceType.IMAGE:
                job = jobs.get(ProcessingJobType.IMAGE_OCR)
                ocr_result = self._ocr.get_by_job_id(job.job_id) if job else None
                if ocr_result:
                    for block in ocr_result.blocks:
                        for line_number, line in enumerate(block.text.splitlines(), 1):
                            add(
                                source.source_id,
                                AttributeExtractionEvidenceType.IMAGE_OCR,
                                line,
                                f"regionId={block.region_id};blockId={block.block_id};lineNumber={line_number}",
                                block.confidence_bp,
                            )
        return tuple(items), tuple(warnings)

    def _completed(
        self, product_id: UUID, source_id: UUID
    ) -> dict[ProcessingJobType, ProcessingJob]:
        found: dict[ProcessingJobType, ProcessingJob] = {}
        cursor: str | None = None
        while True:
            page = self._jobs.list_by_source(product_id, source_id, limit=100, cursor=cursor)
            for job in page.items:
                if job.status is ProcessingJobStatus.COMPLETED and job.job_type not in found:
                    found[job.job_type] = job
            cursor = page.next_cursor
            if cursor is None:
                return found
