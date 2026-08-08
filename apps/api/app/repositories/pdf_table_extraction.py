"""PDF table-extraction result repository contract."""

from typing import Protocol
from uuid import UUID

from app.domain.pdf_table_extraction import PdfTableExtractionResult


class PdfTableExtractionRepository(Protocol):
    def create(self, result: PdfTableExtractionResult) -> PdfTableExtractionResult: ...
    def get_by_id(self, extraction_id: UUID) -> PdfTableExtractionResult | None: ...
    def get_by_job_id(self, job_id: UUID) -> PdfTableExtractionResult | None: ...
