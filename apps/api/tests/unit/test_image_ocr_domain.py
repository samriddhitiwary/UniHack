"""OCR evidence domain invariants and normalization tests."""

from dataclasses import FrozenInstanceError, replace

import pytest

from app.domain.image_ocr import ImageOcrResult, create_ocr_text_block, normalize_ocr_text
from tests.fixtures.image_ocr import make_image_ocr_result, make_ocr_block


def test_text_normalization_is_conservative_and_preserves_evidence() -> None:
    value = "\x00  Model:  MX-42\r\n415   V\t50 Hz  "
    assert normalize_ocr_text(value) == "Model: MX-42\n415 V 50 Hz"


def test_block_has_integer_confidence_and_oriented_relative_box() -> None:
    block = make_ocr_block()
    assert (block.confidence_bp, block.x, block.y, block.width, block.height) == (
        9_000,
        10,
        20,
        100,
        20,
    )
    assert (
        block.relative_x_bp,
        block.relative_y_bp,
        block.relative_width_bp,
        block.relative_height_bp,
    ) == (250, 1_000, 2_500, 1_000)


def test_blocks_and_results_are_immutable_and_utc_safe() -> None:
    result = make_image_ocr_result()
    with pytest.raises(FrozenInstanceError):
        result.block_count = 9  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.blocks[0].text = "changed"  # type: ignore[misc]
    assert result.created_at.utcoffset() is not None


def test_result_aggregate_invariants_are_enforced() -> None:
    result = make_image_ocr_result()
    with pytest.raises(ValueError):
        replace(result, block_count=2)
    with pytest.raises(ValueError):
        replace(result, total_character_count=1)
    with pytest.raises(ValueError):
        replace(result, average_confidence_bp=1)


def test_out_of_bounds_box_and_raw_float_are_rejected() -> None:
    with pytest.raises(ValueError):
        create_ocr_text_block(
            block_id="block-1",
            region_id="region-1",
            reading_order=1,
            text="415 V",
            confidence_bp=9_000,
            x=390,
            y=0,
            width=20,
            height=10,
            image_width=400,
            image_height=200,
        )
    with pytest.raises((TypeError, ValueError)):
        create_ocr_text_block(
            block_id="block-1",
            region_id="region-1",
            reading_order=1,
            text="415 V",
            confidence_bp=90.0,  # type: ignore[arg-type]
            x=0,
            y=0,
            width=10,
            height=10,
            image_width=400,
            image_height=200,
        )


def test_result_identity_linkage_is_preserved() -> None:
    result: ImageOcrResult = make_image_ocr_result()
    assert result.job_id and result.product_id and result.source_id and result.image_analysis_id
