"""Bounded conversion of available extraction results into classification evidence."""

from uuid import UUID

from app.core.exceptions import ProductClassificationEvidenceLimitExceededError
from app.domain.processing_jobs import ProcessingJob, ProcessingJobStatus, ProcessingJobType
from app.domain.product_classification import ClassificationEvidence, ClassificationEvidenceType
from app.domain.product_sources import ProductSource, ProductSourceType
from app.repositories.csv_processing import CsvProcessingResultRepository
from app.repositories.image_ocr import ImageOcrResultRepository
from app.repositories.pdf_extraction import PdfExtractionResultRepository
from app.repositories.pdf_table_extraction import PdfTableExtractionRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_sources import ProductSourceRepository


class ProductClassificationEvidenceAggregator:
    def __init__(
        self,
        *,
        source_repository: ProductSourceRepository,
        job_repository: ProcessingJobRepository,
        pdf_text_repository: PdfExtractionResultRepository,
        pdf_table_repository: PdfTableExtractionRepository,
        csv_repository: CsvProcessingResultRepository,
        image_ocr_repository: ImageOcrResultRepository,
        max_items: int = 5_000,
        max_total_characters: int = 500_000,
        max_item_characters: int = 5_000,
    ) -> None:
        if min(max_items, max_total_characters, max_item_characters) < 1:
            raise ValueError("classification evidence limits must be positive")
        self._sources = source_repository
        self._jobs = job_repository
        self._pdf_text = pdf_text_repository
        self._pdf_tables = pdf_table_repository
        self._csv = csv_repository
        self._ocr = image_ocr_repository
        self._max_items = max_items
        self._max_total = max_total_characters
        self._max_item = max_item_characters

    def collect(self, product_id: UUID) -> tuple[ClassificationEvidence, ...]:
        sources: list[ProductSource] = []
        cursor: str | None = None
        while True:
            page = self._sources.list_by_product(product_id, limit=100, cursor=cursor)
            sources.extend(page.items)
            cursor = page.next_cursor
            if cursor is None:
                break
        evidence: list[ClassificationEvidence] = []
        total = 0

        def add(
            source_id: UUID,
            evidence_type: ClassificationEvidenceType,
            text: str,
            location: str,
            weight: int,
        ) -> None:
            nonlocal total
            normalized = text.replace("\x00", "").strip()
            if not normalized:
                return
            if (
                len(normalized) > self._max_item
                or len(evidence) + 1 > self._max_items
                or total + len(normalized) > self._max_total
            ):
                raise ProductClassificationEvidenceLimitExceededError(
                    "classification evidence exceeds configured bounds"
                )
            evidence.append(
                ClassificationEvidence(
                    evidence_id=f"evidence-{len(evidence) + 1:06d}",
                    source_id=source_id,
                    evidence_type=evidence_type,
                    text=normalized,
                    location=location,
                    weight=weight,
                )
            )
            total += len(normalized)

        for source in sources:
            if source.source_type is ProductSourceType.TEXT:
                if source.text_content:
                    add(
                        source.source_id,
                        ClassificationEvidenceType.DIRECT_TEXT,
                        source.text_content,
                        f"sourceId={source.source_id}",
                        100,
                    )
                continue
            completed = self._completed_jobs(source)
            if source.source_type is ProductSourceType.PDF:
                text_job = completed.get(ProcessingJobType.PDF_TEXT_EXTRACTION)
                if text_job:
                    text_result = self._pdf_text.get_by_job_id(text_job.job_id)
                    if text_result:
                        for pdf_page in text_result.pages:
                            add(
                                source.source_id,
                                ClassificationEvidenceType.PDF_TEXT,
                                pdf_page.text,
                                f"pageNumber={pdf_page.page_number}",
                                100,
                            )
                table_job = completed.get(ProcessingJobType.PDF_TABLE_EXTRACTION)
                if table_job:
                    table_result = self._pdf_tables.get_by_job_id(table_job.job_id)
                    if table_result:
                        for table in table_result.tables:
                            for table_row in table.rows:
                                for table_cell in table_row.cells:
                                    add(
                                        source.source_id,
                                        ClassificationEvidenceType.PDF_TABLE_CELL,
                                        table_cell.text,
                                        f"pageNumber={table.page_number};tableIndex={table.table_index};rowIndex={table_row.row_index};columnIndex={table_cell.column_index}",
                                        110,
                                    )
            elif source.source_type is ProductSourceType.CSV:
                job = completed.get(ProcessingJobType.CSV_PROCESSING)
                csv_result = self._csv.get_by_job_id(job.job_id) if job else None
                if csv_result:
                    for header in csv_result.header:
                        add(
                            source.source_id,
                            ClassificationEvidenceType.CSV_HEADER,
                            header.text,
                            f"columnIndex={header.column_index}",
                            110,
                        )
                    for csv_row in csv_result.rows:
                        for csv_cell in csv_row.cells + csv_row.extra_cells:
                            header_name = (
                                csv_result.header[csv_cell.column_index].text
                                if csv_cell.column_index < len(csv_result.header)
                                else ""
                            )
                            add(
                                source.source_id,
                                ClassificationEvidenceType.CSV_CELL,
                                csv_cell.text,
                                f"rowNumber={csv_row.row_number};columnIndex={csv_cell.column_index};headerName={header_name}"[
                                    :500
                                ],
                                90,
                            )
            elif source.source_type is ProductSourceType.IMAGE:
                job = completed.get(ProcessingJobType.IMAGE_OCR)
                ocr_result = self._ocr.get_by_job_id(job.job_id) if job else None
                if ocr_result:
                    for block in ocr_result.blocks:
                        add(
                            source.source_id,
                            ClassificationEvidenceType.IMAGE_OCR,
                            block.text,
                            f"regionId={block.region_id};blockId={block.block_id}",
                            100 * block.confidence_bp // 10_000,
                        )
        return tuple(evidence)

    def _completed_jobs(self, source: ProductSource) -> dict[ProcessingJobType, ProcessingJob]:
        found: dict[ProcessingJobType, ProcessingJob] = {}
        cursor: str | None = None
        while True:
            page = self._jobs.list_by_source(
                source.product_id, source.source_id, limit=100, cursor=cursor
            )
            for job in page.items:
                if job.status is ProcessingJobStatus.COMPLETED and job.job_type not in found:
                    found[job.job_type] = job
            cursor = page.next_cursor
            if cursor is None:
                return found
