"""Conservative overlapping-region OCR duplicate suppression tests."""

from app.domain.image_ocr import deduplicate_ocr_blocks
from tests.fixtures.image_ocr import make_ocr_block


def test_overlapping_exact_duplicate_keeps_higher_confidence_and_counts() -> None:
    lower = make_ocr_block(region_id="region-000001", confidence_bp=7_000)
    higher = make_ocr_block(block_id="block-000002", region_id="region-000002", confidence_bp=9_000)
    blocks, duplicate_count = deduplicate_ocr_blocks((lower, higher))
    assert duplicate_count == 1 and len(blocks) == 1
    assert blocks[0].confidence_bp == 9_000 and blocks[0].region_id == "region-000002"
    assert (blocks[0].block_id, blocks[0].reading_order) == ("block-000001", 1)


def test_whitespace_equivalent_duplicate_is_suppressed_deterministically() -> None:
    first = make_ocr_block(text="MODEL\nMX-42", confidence_bp=8_000)
    second = make_ocr_block(
        block_id="block-2", region_id="region-2", text="MODEL MX-42", confidence_bp=7_000
    )
    assert deduplicate_ocr_blocks((first, second)) == deduplicate_ocr_blocks((first, second))
    assert deduplicate_ocr_blocks((first, second))[1] == 1


def test_nonoverlapping_or_distinct_model_values_are_preserved() -> None:
    first = make_ocr_block(text="MX-42")
    nonoverlap = make_ocr_block(block_id="block-2", region_id="region-2", text="MX-42", x=200)
    distinct = make_ocr_block(
        block_id="block-3", region_id="region-3", text="MX-43", confidence_bp=9_100
    )
    blocks, duplicate_count = deduplicate_ocr_blocks((first, nonoverlap, distinct))
    assert len(blocks) == 3 and duplicate_count == 0
