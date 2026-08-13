"""SPEC-019 region reuse, orientation, in-memory crops, and OCR limit tests."""

from dataclasses import replace
from io import BytesIO

import pytest
from PIL import Image

from app.core.exceptions import (
    ImageOcrBlockLimitExceededError,
    ImageOcrRegionInvalidError,
    ImageOcrRegionLimitExceededError,
    ImageOcrTextLimitExceededError,
)
from app.domain.image_analysis import ImageOrientation
from app.services.image_ocr_pipeline import (
    ImageOcrLimits,
    load_oriented_image,
    recognize_regions,
    select_ocr_regions,
)
from app.services.ocr_engine import OcrEngineBlock
from tests.fixtures.image_analysis import make_image_analysis_result, make_image_bytes


class FakeEngine:
    engine_name = "FakeOCR"
    engine_version = "1"

    def __init__(self, responses=()) -> None:
        self.responses = list(responses)
        self.sizes: list[tuple[int, int]] = []

    def recognize(self, image: Image.Image) -> tuple[OcrEngineBlock, ...]:
        self.sizes.append(image.size)
        return self.responses.pop(0) if self.responses else ()


def raw_block(
    text: str = "MOTOR 415 V",
    confidence_bp: int = 9_000,
    *,
    x: int = 10,
    y: int = 20,
    width: int = 100,
    height: int = 20,
) -> OcrEngineBlock:
    return OcrEngineBlock(
        text=text,
        confidence_bp=confidence_bp,
        x=x,
        y=y,
        width=width,
        height=height,
    )


def limits(**changes: int) -> ImageOcrLimits:
    values = dict(
        max_regions=6,
        max_blocks=5_000,
        max_total_characters=500_000,
        max_block_characters=10_000,
        minimum_confidence_bp=4_000,
    )
    values.update(changes)
    return ImageOcrLimits(**values)


def test_region_selection_reuses_deterministic_full_then_center_order() -> None:
    analysis = make_image_analysis_result()
    selected = select_ocr_regions(analysis, 2)
    assert selected == analysis.regions[:2]
    assert [region.region_type.value for region in selected] == ["FULL_IMAGE", "CENTER"]


def test_multiple_regions_are_cropped_in_memory_and_reading_order_preserved() -> None:
    analysis = make_image_analysis_result()
    engine = FakeEngine([((raw_block("A"), raw_block("B", x=120)),), ()])
    # Flatten the first response into the engine's expected tuple.
    engine.responses[0] = (raw_block("A"), raw_block("B", x=120, width=50))
    image = Image.new("RGB", (400, 200))
    evidence = recognize_regions(
        image,
        analysis=analysis,
        regions=analysis.regions[:2],
        engine=engine,
        limits=limits(),
    )
    assert engine.sizes == [(400, 200), (200, 100)]
    assert [block.text for block in evidence.blocks] == ["A", "B"]
    assert [block.reading_order for block in evidence.blocks] == [1, 2]


def test_overlapping_region_evidence_is_mapped_globally_then_deduplicated() -> None:
    analysis = make_image_analysis_result()
    engine = FakeEngine(
        [
            (raw_block(x=110, y=70, confidence_bp=7_000),),
            (raw_block(x=10, y=20, confidence_bp=9_000),),
        ]
    )
    evidence = recognize_regions(
        Image.new("RGB", (400, 200)),
        analysis=analysis,
        regions=analysis.regions[:2],
        engine=engine,
        limits=limits(),
    )
    assert evidence.duplicate_block_count == 1 and len(evidence.blocks) == 1
    assert (evidence.blocks[0].x, evidence.blocks[0].y) == (110, 70)
    assert evidence.blocks[0].confidence_bp == 9_000


def test_rotated_orientation_maps_image_regions_and_boxes_to_oriented_coordinates() -> None:
    base = make_image_analysis_result()
    analysis = replace(
        base, metadata=replace(base.metadata, orientation=ImageOrientation.ROTATED_90)
    )
    engine = FakeEngine([(raw_block(width=50),)])
    evidence = recognize_regions(
        Image.new("RGB", (200, 400)),
        analysis=analysis,
        regions=analysis.regions[:1],
        engine=engine,
        limits=limits(),
    )
    assert (evidence.image_width, evidence.image_height) == (200, 400)
    assert (evidence.blocks[0].x, evidence.blocks[0].y) == (10, 20)


def test_source_image_is_loaded_and_oriented_in_memory_without_output_files() -> None:
    data = make_image_bytes("JPEG", orientation=6)
    base = make_image_analysis_result()
    analysis = replace(
        base,
        metadata=replace(
            base.metadata,
            format="JPEG",
            mime_type="image/jpeg",
            orientation=ImageOrientation.ROTATED_90,
            file_size_bytes=len(data),
        ),
    )
    with load_oriented_image(
        BytesIO(data),
        analysis=analysis,
        expected_mime_type="image/jpeg",
        expected_size_bytes=len(data),
    ) as image:
        assert image.size == (200, 400)


def test_region_block_and_text_limits_fail_without_truncation() -> None:
    analysis = make_image_analysis_result()
    image = Image.new("RGB", (400, 200))
    with pytest.raises(ImageOcrRegionLimitExceededError):
        recognize_regions(
            image,
            analysis=analysis,
            regions=analysis.regions[:2],
            engine=FakeEngine(),
            limits=limits(max_regions=1),
        )
    with pytest.raises(ImageOcrBlockLimitExceededError):
        recognize_regions(
            image,
            analysis=analysis,
            regions=analysis.regions[:1],
            engine=FakeEngine([tuple(raw_block(str(index), x=index) for index in range(2))]),
            limits=limits(max_blocks=1),
        )
    with pytest.raises(ImageOcrTextLimitExceededError):
        recognize_regions(
            image,
            analysis=analysis,
            regions=analysis.regions[:1],
            engine=FakeEngine([(raw_block("too long"),)]),
            limits=limits(max_block_characters=3),
        )
    with pytest.raises(ImageOcrTextLimitExceededError):
        recognize_regions(
            image,
            analysis=analysis,
            regions=analysis.regions[:1],
            engine=FakeEngine([(raw_block("ab"), raw_block("cd", x=120, width=50))]),
            limits=limits(max_total_characters=3),
        )


def test_engine_box_must_be_inside_its_crop() -> None:
    analysis = make_image_analysis_result()
    with pytest.raises(ImageOcrRegionInvalidError):
        recognize_regions(
            Image.new("RGB", (400, 200)),
            analysis=analysis,
            regions=analysis.regions[:1],
            engine=FakeEngine([(raw_block(x=390, width=20),)]),
            limits=limits(),
        )
