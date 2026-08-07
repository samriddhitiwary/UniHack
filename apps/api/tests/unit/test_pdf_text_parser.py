"""Bounded pypdf page extraction tests."""

from io import BytesIO

import pytest

from app.core.exceptions import (
    PdfExtractionPageLimitExceededError,
    PdfExtractionTextLimitExceededError,
    PdfParseError,
)
from app.services.pdf_text_parser import PdfExtractionLimits, PdfTextParser
from tests.fixtures.pdf_extraction import make_pdf_bytes


def parser(**changes: int) -> PdfTextParser:
    values = {"max_pages": 10, "max_page_characters": 1_000, "max_total_characters": 5_000}
    values.update(changes)
    return PdfTextParser(PdfExtractionLimits(**values))


def test_extracts_single_page_and_multiline_text() -> None:
    pages = parser().extract_pages(BytesIO(make_pdf_bytes([["Pump PX-400", "Pressure 16 bar"]])))
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert pages[0].text == "Pump PX-400\nPressure 16 bar"
    assert pages[0].character_count == len(pages[0].text) and pages[0].has_text is True


def test_extracts_multiple_pages_and_preserves_blank_middle_page() -> None:
    pages = parser().extract_pages(BytesIO(make_pdf_bytes([["First page"], [], ["Third page"]])))
    assert [page.page_number for page in pages] == [1, 2, 3]
    assert [page.text for page in pages] == ["First page", "", "Third page"]
    assert pages[1].character_count == 0 and pages[1].has_text is False


def test_all_blank_pages_are_valid_parser_output() -> None:
    pages = parser().extract_pages(BytesIO(make_pdf_bytes([[], []])))
    assert len(pages) == 2 and not any(page.has_text for page in pages)


def test_corrupt_or_zero_page_pdf_is_controlled() -> None:
    with pytest.raises(PdfParseError):
        parser().extract_pages(BytesIO(b"not a PDF"))


def test_page_limit_is_rejected_without_truncation() -> None:
    with pytest.raises(PdfExtractionPageLimitExceededError):
        parser(max_pages=1).extract_pages(BytesIO(make_pdf_bytes([["one"], ["two"]])))


def test_per_page_text_limit_is_rejected_without_truncation() -> None:
    with pytest.raises(PdfExtractionTextLimitExceededError):
        parser(max_page_characters=4).extract_pages(BytesIO(make_pdf_bytes([["12345"]])))


def test_total_text_limit_is_rejected_without_truncation() -> None:
    with pytest.raises(PdfExtractionTextLimitExceededError):
        parser(max_total_characters=8).extract_pages(
            BytesIO(make_pdf_bytes([["12345"], ["67890"]]))
        )


@pytest.mark.parametrize(
    "values",
    [
        {"max_pages": 0},
        {"max_page_characters": -1},
        {"max_total_characters": 0},
        {"max_pages": True},
    ],
)
def test_limits_must_be_positive_integers(values: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        PdfExtractionLimits(**values)
