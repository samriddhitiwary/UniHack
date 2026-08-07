"""Immutable page-level PDF text-extraction evidence."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from app.domain.pdf_extraction.enums import PdfExtractionQualityStatus

PARSER_NAME_MAX_LENGTH = 50
PARSER_VERSION_MAX_LENGTH = 50
WARNING_CODE_MAX_LENGTH = 100
LOW_TEXT_AVERAGE_CHARACTERS = 25


def normalize_pdf_text(value: str) -> str:
    """Apply conservative, non-semantic parser-output normalization."""
    if not isinstance(value, str):
        raise ValueError("PDF page text must be a string")
    return value.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n").strip()


@dataclass(frozen=True, slots=True)
class PdfExtractionPage:
    page_number: int
    text: str
    character_count: int
    has_text: bool

    def __post_init__(self) -> None:
        if (
            isinstance(self.page_number, bool)
            or not isinstance(self.page_number, int)
            or self.page_number < 1
        ):
            raise ValueError("page_number must be a positive integer")
        if self.text != normalize_pdf_text(self.text):
            raise ValueError("page text must be conservatively normalized")
        if self.character_count != len(self.text):
            raise ValueError("character_count must equal normalized text length")
        if self.has_text is not (self.character_count > 0):
            raise ValueError("has_text must match character_count")

    @classmethod
    def create(cls, page_number: int, raw_text: str) -> Self:
        text = normalize_pdf_text(raw_text)
        return cls(
            page_number=page_number,
            text=text,
            character_count=len(text),
            has_text=bool(text),
        )


def assess_pdf_extraction_quality(
    pages: tuple[PdfExtractionPage, ...],
) -> PdfExtractionQualityStatus:
    total = sum(page.character_count for page in pages)
    if total == 0:
        return PdfExtractionQualityStatus.NO_TEXT
    if total / len(pages) < LOW_TEXT_AVERAGE_CHARACTERS:
        return PdfExtractionQualityStatus.LOW_TEXT
    return PdfExtractionQualityStatus.USABLE


@dataclass(frozen=True, slots=True, kw_only=True)
class PdfTextExtractionResult:
    extraction_id: UUID
    job_id: UUID
    product_id: UUID
    source_id: UUID
    parser: str
    parser_version: str
    page_count: int
    pages_with_text: int
    total_character_count: int
    quality_status: PdfExtractionQualityStatus
    pages: tuple[PdfExtractionPage, ...]
    warning_codes: tuple[str, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        for field, value in (
            ("extraction_id", self.extraction_id),
            ("job_id", self.job_id),
            ("product_id", self.product_id),
            ("source_id", self.source_id),
        ):
            if not isinstance(value, UUID):
                raise ValueError(f"{field} must be a UUID")
        if not self.parser.strip() or len(self.parser) > PARSER_NAME_MAX_LENGTH:
            raise ValueError("parser must be nonempty and bounded")
        if not self.parser_version.strip() or len(self.parser_version) > PARSER_VERSION_MAX_LENGTH:
            raise ValueError("parser_version must be nonempty and bounded")
        if not self.pages:
            raise ValueError("extraction result must preserve at least one PDF page")
        if self.page_count != len(self.pages):
            raise ValueError("page_count must equal the number of pages")
        if tuple(page.page_number for page in self.pages) != tuple(range(1, self.page_count + 1)):
            raise ValueError("pages must be ordered and consecutively numbered from one")
        if self.pages_with_text != sum(page.has_text for page in self.pages):
            raise ValueError("pages_with_text must match page evidence")
        if self.total_character_count != sum(page.character_count for page in self.pages):
            raise ValueError("total_character_count must match page evidence")
        if self.quality_status is not assess_pdf_extraction_quality(self.pages):
            raise ValueError("quality_status must match deterministic assessment")
        if len(set(self.warning_codes)) != len(self.warning_codes):
            raise ValueError("warning_codes must be unique")
        if any(
            not code.strip() or len(code) > WARNING_CODE_MAX_LENGTH for code in self.warning_codes
        ):
            raise ValueError("warning_codes must contain bounded nonempty values")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "parser", self.parser.strip())
        object.__setattr__(self, "parser_version", self.parser_version.strip())
        object.__setattr__(
            self,
            "warning_codes",
            tuple(code.strip() for code in self.warning_codes),
        )
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))

    @classmethod
    def create(
        cls,
        *,
        job_id: UUID,
        product_id: UUID,
        source_id: UUID,
        parser: str,
        parser_version: str,
        pages: tuple[PdfExtractionPage, ...],
        now: datetime | None = None,
    ) -> Self:
        quality = assess_pdf_extraction_quality(pages)
        warning_codes: tuple[str, ...] = ()
        if quality is PdfExtractionQualityStatus.NO_TEXT:
            warning_codes = ("NO_EMBEDDED_TEXT",)
        elif quality is PdfExtractionQualityStatus.LOW_TEXT:
            warning_codes = ("LOW_EMBEDDED_TEXT",)
        return cls(
            extraction_id=uuid4(),
            job_id=job_id,
            product_id=product_id,
            source_id=source_id,
            parser=parser,
            parser_version=parser_version,
            page_count=len(pages),
            pages_with_text=sum(page.has_text for page in pages),
            total_character_count=sum(page.character_count for page in pages),
            quality_status=quality,
            pages=pages,
            warning_codes=warning_codes,
            created_at=(now or datetime.now(UTC)).astimezone(UTC),
        )
