"""PDF text-extraction result repository contract."""

from typing import Protocol
from uuid import UUID

from app.domain.pdf_extraction import PdfTextExtractionResult


class PdfExtractionResultRepository(Protocol):
    def create(self, result: PdfTextExtractionResult) -> PdfTextExtractionResult: ...

    def get_by_id(self, extraction_id: UUID) -> PdfTextExtractionResult | None: ...

    def get_by_job_id(self, job_id: UUID) -> PdfTextExtractionResult | None: ...
