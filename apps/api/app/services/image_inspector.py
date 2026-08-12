"""Bounded Pillow image validation, metadata inspection, and geometry generation."""

import warnings
from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO

import PIL
from PIL import Image, UnidentifiedImageError

from app.core.exceptions import (
    ImageAnalysisError,
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
from app.domain.image_analysis import (
    ImageAnalysisRegion,
    ImageMetadata,
    ImageOrientation,
    assess_nameplate_candidate,
    generate_analysis_regions,
)

PARSER_NAME = "Pillow"
PARSER_VERSION = PIL.__version__
READ_CHUNK_BYTES = 64 * 1024
SUPPORTED_MIME_FORMATS = {
    "image/png": "PNG",
    "image/jpeg": "JPEG",
    "image/webp": "WEBP",
}


@dataclass(frozen=True, slots=True)
class ImageAnalysisLimits:
    max_file_bytes: int = 10 * 1024 * 1024
    max_width: int = 12_000
    max_height: int = 12_000
    max_pixels: int = 80_000_000
    max_regions: int = 16

    def __post_init__(self) -> None:
        for name, value in (
            ("max_file_bytes", self.max_file_bytes),
            ("max_width", self.max_width),
            ("max_height", self.max_height),
            ("max_pixels", self.max_pixels),
            ("max_regions", self.max_regions),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class InspectedImage:
    metadata: ImageMetadata
    regions: tuple[ImageAnalysisRegion, ...]


class ImageInspector:
    def __init__(self, limits: ImageAnalysisLimits) -> None:
        self._limits = limits

    def inspect(
        self,
        stream: BinaryIO,
        *,
        expected_mime_type: str,
        expected_size_bytes: int | None = None,
    ) -> InspectedImage:
        expected_format = SUPPORTED_MIME_FORMATS.get(expected_mime_type)
        if expected_format is None:
            raise ImageFormatUnsupportedError()
        raw = self._read_bounded(stream)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(raw)) as image:
                    decoded_format = (image.format or "").upper()
                    if decoded_format not in set(SUPPORTED_MIME_FORMATS.values()):
                        raise ImageFormatUnsupportedError()
                    if decoded_format != expected_format:
                        raise ImageFormatMismatchError()
                    if getattr(image, "n_frames", 1) != 1:
                        raise ImageAnimationNotSupportedError()
                    width, height = image.size
                    self._validate_geometry(width, height)
                    image.verify()
                with Image.open(BytesIO(raw)) as metadata_image:
                    mode = metadata_image.mode
                    bands = metadata_image.getbands()
                    orientation = _orientation(metadata_image.getexif().get(274))
        except ImageAnalysisError:
            raise
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise ImageAnalysisPixelLimitExceededError() from exc
        except (UnidentifiedImageError, OSError, RuntimeError, SyntaxError, ValueError) as exc:
            raise ImageDecodeError() from exc
        metadata = ImageMetadata(
            format=decoded_format,
            mime_type=expected_mime_type,
            width=width,
            height=height,
            pixel_count=width * height,
            aspect_ratio_numerator=width,
            aspect_ratio_denominator=height,
            color_mode=mode,
            has_alpha="A" in bands,
            is_grayscale=mode in {"1", "L", "LA"},
            orientation=orientation,
            file_size_bytes=len(raw),
        )
        _, score = assess_nameplate_candidate(width, height)
        regions = generate_analysis_regions(width, height, score)
        if len(regions) > self._limits.max_regions:
            raise ImageAnalysisRegionLimitExceededError()
        return InspectedImage(metadata, regions)

    def _read_bounded(self, stream: BinaryIO) -> bytes:
        parts: list[bytes] = []
        total = 0
        while True:
            remaining = self._limits.max_file_bytes + 1 - total
            chunk = stream.read(min(READ_CHUNK_BYTES, remaining))
            if not chunk:
                if total == 0:
                    raise ImageDecodeError()
                return b"".join(parts)
            if not isinstance(chunk, bytes):
                raise ImageDecodeError()
            parts.append(chunk)
            total += len(chunk)
            if total > self._limits.max_file_bytes:
                raise ImageAnalysisFileSizeLimitExceededError()

    def _validate_geometry(self, width: int, height: int) -> None:
        if width > self._limits.max_width:
            raise ImageAnalysisWidthLimitExceededError()
        if height > self._limits.max_height:
            raise ImageAnalysisHeightLimitExceededError()
        if width * height > self._limits.max_pixels:
            raise ImageAnalysisPixelLimitExceededError()


def _orientation(value: object) -> ImageOrientation:
    if value in (None, 1):
        return ImageOrientation.NORMAL
    if value == 3:
        return ImageOrientation.ROTATED_180
    if value == 6:
        return ImageOrientation.ROTATED_90
    if value == 8:
        return ImageOrientation.ROTATED_270
    if value in {2, 4, 5, 7}:
        return ImageOrientation.MIRRORED
    return ImageOrientation.UNKNOWN
