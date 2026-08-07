"""PDF extraction evidence, normalization, and quality tests."""

from dataclasses import FrozenInstanceError

import pytest

from app.domain.pdf_extraction import (
    PdfExtractionPage,
    PdfExtractionQualityStatus,
    PdfTextExtractionResult,
    assess_pdf_extraction_quality,
    normalize_pdf_text,
)
from tests.fixtures.pdf_extraction import make_pdf_extraction_result


def test_normalization_is_conservative() -> None:
    assert normalize_pdf_text(" \x00Title\r\nValue: 16 bar\rKeep punctuation! ") == (
        "Title\nValue: 16 bar\nKeep punctuation!"
    )


@pytest.mark.parametrize(
    ("texts", "expected"),
    [
        (("", ""), PdfExtractionQualityStatus.NO_TEXT),
        (("tiny", ""), PdfExtractionQualityStatus.LOW_TEXT),
        (("A" * 30, "B" * 30), PdfExtractionQualityStatus.USABLE),
    ],
)
def test_quality_classification_is_deterministic(
    texts: tuple[str, ...], expected: PdfExtractionQualityStatus
) -> None:
    pages = tuple(PdfExtractionPage.create(index, text) for index, text in enumerate(texts, 1))
    assert assess_pdf_extraction_quality(pages) is expected
    assert make_pdf_extraction_result(pages=pages).quality_status is expected


def test_result_tracks_exact_order_counts_and_warnings() -> None:
    pages = (PdfExtractionPage.create(1, "few"), PdfExtractionPage.create(2, ""))
    result = make_pdf_extraction_result(pages=pages)
    assert result.page_count == 2
    assert result.pages_with_text == 1
    assert result.total_character_count == 3
    assert result.warning_codes == ("LOW_EMBEDDED_TEXT",)
    with pytest.raises(FrozenInstanceError):
        result.page_count = 3  # type: ignore[misc]


@pytest.mark.parametrize(
    "page",
    [
        lambda: PdfExtractionPage(0, "", 0, False),
        lambda: PdfExtractionPage(1, " x ", 3, True),
        lambda: PdfExtractionPage(1, "x", 2, True),
        lambda: PdfExtractionPage(1, "", 0, True),
    ],
)
def test_invalid_page_invariants_are_rejected(page: object) -> None:
    with pytest.raises(ValueError):
        page()  # type: ignore[operator]


def test_result_rejects_missing_or_out_of_order_pages() -> None:
    result = make_pdf_extraction_result()
    values = {field: getattr(result, field) for field in result.__dataclass_fields__}
    values["pages"] = (PdfExtractionPage.create(2, "text"),)
    values["page_count"] = 1
    values["pages_with_text"] = 1
    values["total_character_count"] = 4
    with pytest.raises(ValueError):
        PdfTextExtractionResult(**values)
