"""PDF text-extraction domain model."""

from app.domain.pdf_extraction.entities import (
    LOW_TEXT_AVERAGE_CHARACTERS,
    PdfExtractionPage,
    PdfTextExtractionResult,
    assess_pdf_extraction_quality,
    normalize_pdf_text,
)
from app.domain.pdf_extraction.enums import PdfExtractionQualityStatus

__all__ = [
    "LOW_TEXT_AVERAGE_CHARACTERS",
    "PdfExtractionPage",
    "PdfExtractionQualityStatus",
    "PdfTextExtractionResult",
    "assess_pdf_extraction_quality",
    "normalize_pdf_text",
]
