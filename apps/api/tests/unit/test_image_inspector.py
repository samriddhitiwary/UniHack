"""Pillow image validation, metadata, formats, and limits tests."""

from io import BytesIO

import pytest
from PIL import Image

from app.core.exceptions import (
    ImageAnalysisFileSizeLimitExceededError,
    ImageAnalysisHeightLimitExceededError,
    ImageAnalysisPixelLimitExceededError,
    ImageAnalysisRegionLimitExceededError,
    ImageAnalysisWidthLimitExceededError,
    ImageAnimationNotSupportedError,
    ImageDecodeError,
    ImageFormatMismatchError,
    ImageFormatUnsupportedError,
)
from app.domain.image_analysis import ImageOrientation
from app.services.image_inspector import ImageAnalysisLimits, ImageInspector
from tests.fixtures.image_analysis import make_image_bytes


def inspector(**changes: int) -> ImageInspector:
    values = dict(
        max_file_bytes=1_000_000,
        max_width=2_000,
        max_height=2_000,
        max_pixels=2_000_000,
        max_regions=16,
    )
    values.update(changes)
    return ImageInspector(ImageAnalysisLimits(**values))


@pytest.mark.parametrize(
    ("format", "mime"), [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")]
)
def test_supported_formats_are_decoded_and_mime_matched(format: str, mime: str) -> None:
    result = inspector().inspect(BytesIO(make_image_bytes(format)), expected_mime_type=mime)
    assert result.metadata.format == format and result.metadata.mime_type == mime
    assert (result.metadata.width, result.metadata.height, result.metadata.pixel_count) == (
        400,
        200,
        80_000,
    )


def test_metadata_modes_alpha_grayscale_and_aspect_integers() -> None:
    rgba = inspector().inspect(
        BytesIO(make_image_bytes(mode="RGBA")), expected_mime_type="image/png"
    )
    assert rgba.metadata.color_mode == "RGBA" and rgba.metadata.has_alpha
    gray = inspector().inspect(BytesIO(make_image_bytes(mode="L")), expected_mime_type="image/png")
    assert gray.metadata.is_grayscale and not gray.metadata.has_alpha
    assert (gray.metadata.aspect_ratio_numerator, gray.metadata.aspect_ratio_denominator) == (
        400,
        200,
    )


@pytest.mark.parametrize(
    ("orientation", "expected"),
    [
        (1, ImageOrientation.NORMAL),
        (3, ImageOrientation.ROTATED_180),
        (6, ImageOrientation.ROTATED_90),
        (8, ImageOrientation.ROTATED_270),
        (2, ImageOrientation.MIRRORED),
        (9, ImageOrientation.UNKNOWN),
    ],
)
def test_only_exif_orientation_is_exposed(orientation: int, expected: ImageOrientation) -> None:
    data = make_image_bytes("JPEG", orientation=orientation)
    assert (
        inspector().inspect(BytesIO(data), expected_mime_type="image/jpeg").metadata.orientation
        is expected
    )


def test_mismatch_unsupported_corrupt_and_animated_images_are_controlled() -> None:
    with pytest.raises(ImageFormatMismatchError):
        inspector().inspect(BytesIO(make_image_bytes("PNG")), expected_mime_type="image/jpeg")
    with pytest.raises(ImageFormatUnsupportedError):
        inspector().inspect(BytesIO(make_image_bytes("PNG")), expected_mime_type="image/gif")
    for content, mime_type in (
        (b"bad", "image/png"),
        (make_image_bytes("PNG")[:30], "image/png"),
        (make_image_bytes("JPEG")[:30], "image/jpeg"),
        (make_image_bytes("WEBP")[:30], "image/webp"),
    ):
        with pytest.raises(ImageDecodeError):
            inspector().inspect(BytesIO(content), expected_mime_type=mime_type)
    with pytest.raises(ImageAnimationNotSupportedError):
        inspector().inspect(
            BytesIO(make_image_bytes("WEBP", animated=True)), expected_mime_type="image/webp"
        )


def test_file_dimension_pixel_and_region_limits_are_enforced() -> None:
    data = make_image_bytes(size=(100, 50))
    with pytest.raises(ImageAnalysisFileSizeLimitExceededError):
        inspector(max_file_bytes=len(data) - 1).inspect(
            BytesIO(data), expected_mime_type="image/png"
        )
    with pytest.raises(ImageAnalysisWidthLimitExceededError):
        inspector(max_width=99).inspect(BytesIO(data), expected_mime_type="image/png")
    with pytest.raises(ImageAnalysisHeightLimitExceededError):
        inspector(max_height=49).inspect(BytesIO(data), expected_mime_type="image/png")
    with pytest.raises(ImageAnalysisPixelLimitExceededError):
        inspector(max_pixels=4_999).inspect(BytesIO(data), expected_mime_type="image/png")
    with pytest.raises(ImageAnalysisRegionLimitExceededError):
        inspector(max_regions=5).inspect(BytesIO(data), expected_mime_type="image/png")


def test_pillow_decompression_bomb_warning_is_a_controlled_pixel_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 4_000)
    with pytest.raises(ImageAnalysisPixelLimitExceededError):
        inspector().inspect(
            BytesIO(make_image_bytes(size=(100, 50))), expected_mime_type="image/png"
        )


@pytest.mark.parametrize(
    "field", ["max_file_bytes", "max_width", "max_height", "max_pixels", "max_regions"]
)
def test_limits_must_be_positive(field: str) -> None:
    values = dict(max_file_bytes=1, max_width=1, max_height=1, max_pixels=1, max_regions=1)
    values[field] = 0
    with pytest.raises(ValueError):
        ImageAnalysisLimits(**values)
