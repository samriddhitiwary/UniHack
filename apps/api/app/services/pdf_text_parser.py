"""Bounded embedded-text extraction using pypdf."""

from dataclasses import dataclass
from typing import BinaryIO

import pypdf
from pypdf import PdfReader

from app.core.exceptions import (
    PdfExtractionPageLimitExceededError,
    PdfExtractionTextLimitExceededError,
    PdfParseError,
)
from app.domain.pdf_extraction import PdfExtractionPage

PARSER_NAME = "pypdf"
PARSER_VERSION = pypdf.__version__


@dataclass(frozen=True, slots=True)
class PdfExtractionLimits:
    max_pages: int = 300
    max_total_characters: int = 2_000_000
    max_page_characters: int = 100_000

    def __post_init__(self) -> None:
        for name, value in (
            ("max_pages", self.max_pages),
            ("max_total_characters", self.max_total_characters),
            ("max_page_characters", self.max_page_characters),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")


class PdfTextParser:
    def __init__(self, limits: PdfExtractionLimits) -> None:
        self._limits = limits

    def extract_pages(self, stream: BinaryIO) -> tuple[PdfExtractionPage, ...]:
        try:
            reader = PdfReader(stream, strict=False)
            page_count = len(reader.pages)
        except Exception as exc:
            raise PdfParseError() from exc
        if page_count < 1:
            raise PdfParseError()
        if page_count > self._limits.max_pages:
            raise PdfExtractionPageLimitExceededError()

        pages: list[PdfExtractionPage] = []
        total = 0
        for page_number, pdf_page in enumerate(reader.pages, start=1):
            try:
                page = PdfExtractionPage.create(page_number, pdf_page.extract_text() or "")
            except Exception as exc:
                raise PdfParseError() from exc
            if page.character_count > self._limits.max_page_characters:
                raise PdfExtractionTextLimitExceededError()
            total += page.character_count
            if total > self._limits.max_total_characters:
                raise PdfExtractionTextLimitExceededError()
            pages.append(page)
        return tuple(pages)
