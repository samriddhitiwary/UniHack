"""OCR quality and deterministic nameplate-text heuristic tests."""

import pytest

from app.domain.image_ocr import (
    ImageOcrQualityStatus,
    NameplateTextStatus,
    assess_nameplate_text,
    assess_ocr_quality,
)
from tests.fixtures.image_ocr import make_ocr_block


@pytest.mark.parametrize(
    ("blocks", "expected"),
    [
        ((), ImageOcrQualityStatus.NO_TEXT),
        ((make_ocr_block(confidence_bp=4_000),), ImageOcrQualityStatus.TEXT_FOUND),
        ((make_ocr_block(confidence_bp=3_999),), ImageOcrQualityStatus.LOW_CONFIDENCE_TEXT),
    ],
)
def test_quality_outcomes_are_successful_and_deterministic(blocks, expected) -> None:
    assert assess_ocr_quality(blocks, 4_000) is expected
    assert assess_ocr_quality(blocks, 4_000) is expected


@pytest.mark.parametrize(
    ("text", "status"),
    [
        ("VOLTAGE: 415 V\nFREQ: 50 Hz", NameplateTextStatus.LIKELY_NAMEPLATE_TEXT),
        ("ordinary descriptive prose", NameplateTextStatus.GENERIC_TEXT),
        ("ABC-123", NameplateTextStatus.UNKNOWN),
    ],
)
def test_nameplate_text_heuristic_uses_only_explicit_text_signals(text, status) -> None:
    block = make_ocr_block(text=text)
    actual_status, score = assess_nameplate_text((block,))
    assert actual_status is status and 0 <= score <= 100
    assert assess_nameplate_text((block,)) == (actual_status, score)


def test_no_text_has_no_nameplate_assessment_score() -> None:
    assert assess_nameplate_text(()) == (NameplateTextStatus.NO_TEXT, 0)
