"""Local OCR adapter normalization and optional real-engine tests."""

import builtins
import os

import pytest
from PIL import Image, ImageDraw

from app.core.exceptions import ImageOcrEngineUnavailableError, ImageOcrRegionInvalidError
from app.services.ocr_engine import RapidOcrEngine, confidence_to_basis_points


@pytest.mark.parametrize(
    ("value", "expected"), [(0, 0), (0.4, 4_000), (0.8742, 8_742), (1, 10_000)]
)
def test_confidence_is_normalized_to_integer_basis_points(value, expected) -> None:
    assert confidence_to_basis_points(value) == expected


@pytest.mark.parametrize("value", [-0.1, 1.1, True, "bad"])
def test_invalid_confidence_is_controlled(value) -> None:
    with pytest.raises(ImageOcrRegionInvalidError):
        confidence_to_basis_points(value)


def test_rapidocr_polygon_is_converted_to_bounded_axis_aligned_box() -> None:
    block = RapidOcrEngine._block(
        [[[10.2, 20.8], [109.1, 20.1], [109.9, 40.2], [10.0, 40.9]], "MX-42", 0.9],
        200,
        100,
    )
    assert (block.text, block.confidence_bp) == ("MX-42", 9_000)
    assert (block.x, block.y, block.width, block.height) == (10, 20, 100, 21)


def test_rapidocr_rejects_malformed_or_out_of_bounds_boxes() -> None:
    with pytest.raises(ImageOcrRegionInvalidError):
        RapidOcrEngine._block([[[-1, 0], [10, 0], [10, 10]], "text", 0.9], 20, 20)
    with pytest.raises(ImageOcrRegionInvalidError):
        RapidOcrEngine._block([[], "text", 0.9], 20, 20)


def test_missing_local_engine_dependency_is_a_controlled_startup_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def unavailable(name, *args, **kwargs):
        if name == "rapidocr_onnxruntime":
            raise ImportError("private")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", unavailable)
    with pytest.raises(ImageOcrEngineUnavailableError):
        RapidOcrEngine()


@pytest.mark.skipif(
    os.getenv("RUN_RAPIDOCR_INTEGRATION") != "1",
    reason="set RUN_RAPIDOCR_INTEGRATION=1 to exercise bundled ONNX models",
)
def test_real_rapidocr_engine_recognizes_generated_clear_text() -> None:
    image = Image.new("RGB", (900, 220), "white")
    ImageDraw.Draw(image).text(
        (20, 50), "MOTOR 415 V 50 Hz", fill="black", stroke_width=1, font_size=48
    )
    blocks = RapidOcrEngine().recognize(image)
    assert blocks and any(block.text.strip() for block in blocks)
