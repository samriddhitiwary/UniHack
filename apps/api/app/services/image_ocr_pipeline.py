"""In-memory orientation, SPEC-019 region mapping, OCR, and evidence normalization."""

import warnings
from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO

from PIL import Image, UnidentifiedImageError

from app.core.exceptions import (
    ImageOcrBlockLimitExceededError,
    ImageOcrEngineError,
    ImageOcrError,
    ImageOcrRegionInvalidError,
    ImageOcrRegionLimitExceededError,
    ImageOcrTextLimitExceededError,
)
from app.domain.image_analysis import ImageAnalysisRegion, ImageAnalysisResult, ImageOrientation
from app.domain.image_ocr import (
    OcrTextBlock,
    create_ocr_text_block,
    deduplicate_ocr_blocks,
    normalize_ocr_text,
)
from app.services.image_inspector import SUPPORTED_MIME_FORMATS
from app.services.ocr_engine import OcrEngine


@dataclass(frozen=True, slots=True)
class ImageOcrLimits:
    max_regions: int = 6
    max_blocks: int = 5_000
    max_total_characters: int = 500_000
    max_block_characters: int = 10_000
    minimum_confidence_bp: int = 4_000

    def __post_init__(self) -> None:
        for name, value in (
            ("max_regions", self.max_regions),
            ("max_blocks", self.max_blocks),
            ("max_total_characters", self.max_total_characters),
            ("max_block_characters", self.max_block_characters),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if (
            isinstance(self.minimum_confidence_bp, bool)
            or not isinstance(self.minimum_confidence_bp, int)
            or not 0 <= self.minimum_confidence_bp <= 10_000
        ):
            raise ValueError("minimum_confidence_bp must be from zero to 10000")


@dataclass(frozen=True, slots=True)
class OcrEvidence:
    image_width: int
    image_height: int
    region_count: int
    blocks: tuple[OcrTextBlock, ...]
    duplicate_block_count: int


def select_ocr_regions(
    analysis: ImageAnalysisResult, max_regions: int
) -> tuple[ImageAnalysisRegion, ...]:
    if isinstance(max_regions, bool) or not isinstance(max_regions, int) or max_regions < 1:
        raise ImageOcrRegionLimitExceededError()
    selected = analysis.regions[:max_regions]
    if not selected or selected[0].region_type.value != "FULL_IMAGE":
        raise ImageOcrRegionInvalidError()
    return selected


def load_oriented_image(
    stream: BinaryIO,
    *,
    analysis: ImageAnalysisResult,
    expected_mime_type: str,
    expected_size_bytes: int,
) -> Image.Image:
    """Decode exactly the analyzed object and orient it without mutating storage."""
    raw = _read_exact_bounded(stream, expected_size_bytes)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as source:
                if (source.format or "").upper() != SUPPORTED_MIME_FORMATS[expected_mime_type]:
                    raise ImageOcrEngineError()
                if source.size != (analysis.metadata.width, analysis.metadata.height):
                    raise ImageOcrRegionInvalidError()
                if getattr(source, "n_frames", 1) != 1:
                    raise ImageOcrEngineError()
                source.load()
                oriented = _orient(source, analysis.metadata.orientation)
                return oriented.copy()
    except ImageOcrError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageOcrEngineError() from exc
    except (
        KeyError,
        UnidentifiedImageError,
        OSError,
        RuntimeError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise ImageOcrEngineError() from exc


def _read_exact_bounded(stream: BinaryIO, expected_size_bytes: int) -> bytes:
    if (
        isinstance(expected_size_bytes, bool)
        or not isinstance(expected_size_bytes, int)
        or expected_size_bytes < 1
    ):
        raise ImageOcrEngineError()
    parts: list[bytes] = []
    total = 0
    while total <= expected_size_bytes:
        chunk = stream.read(min(64 * 1024, expected_size_bytes + 1 - total))
        if not chunk:
            break
        if not isinstance(chunk, bytes):
            raise ImageOcrEngineError()
        parts.append(chunk)
        total += len(chunk)
    raw = b"".join(parts)
    if len(raw) != expected_size_bytes:
        raise ImageOcrEngineError()
    return raw


def recognize_regions(
    image: Image.Image,
    *,
    analysis: ImageAnalysisResult,
    regions: tuple[ImageAnalysisRegion, ...],
    engine: OcrEngine,
    limits: ImageOcrLimits,
) -> OcrEvidence:
    if len(regions) > limits.max_regions:
        raise ImageOcrRegionLimitExceededError()
    expected_size = _oriented_size(
        analysis.metadata.width, analysis.metadata.height, analysis.metadata.orientation
    )
    if image.size != expected_size:
        raise ImageOcrRegionInvalidError()
    blocks: list[OcrTextBlock] = []
    total_characters = 0
    for region in regions:
        region_box = _oriented_region_box(
            region,
            analysis.metadata.width,
            analysis.metadata.height,
            analysis.metadata.orientation,
        )
        left, top, width, height = region_box
        if left < 0 or top < 0 or left + width > image.width or top + height > image.height:
            raise ImageOcrRegionInvalidError()
        with image.crop((left, top, left + width, top + height)) as crop:
            recognized = engine.recognize(crop)
        reading_order = 0
        for raw_block in recognized:
            if (
                raw_block.x < 0
                or raw_block.y < 0
                or raw_block.width < 1
                or raw_block.height < 1
                or raw_block.x + raw_block.width > width
                or raw_block.y + raw_block.height > height
            ):
                raise ImageOcrRegionInvalidError()
            text = normalize_ocr_text(raw_block.text)
            if not text:
                continue
            reading_order += 1
            if len(text) > limits.max_block_characters:
                raise ImageOcrTextLimitExceededError()
            total_characters += len(text)
            if total_characters > limits.max_total_characters:
                raise ImageOcrTextLimitExceededError()
            if len(blocks) >= limits.max_blocks:
                raise ImageOcrBlockLimitExceededError()
            try:
                block = create_ocr_text_block(
                    block_id=f"candidate-{len(blocks) + 1:06d}",
                    region_id=region.region_id,
                    reading_order=reading_order,
                    text=text,
                    confidence_bp=raw_block.confidence_bp,
                    x=left + raw_block.x,
                    y=top + raw_block.y,
                    width=raw_block.width,
                    height=raw_block.height,
                    image_width=image.width,
                    image_height=image.height,
                )
            except ValueError as exc:
                raise ImageOcrRegionInvalidError() from exc
            blocks.append(block)
    deduplicated, duplicate_count = deduplicate_ocr_blocks(tuple(blocks))
    return OcrEvidence(image.width, image.height, len(regions), deduplicated, duplicate_count)


def _orient(image: Image.Image, orientation: ImageOrientation) -> Image.Image:
    if orientation is ImageOrientation.ROTATED_90:
        return image.transpose(Image.Transpose.ROTATE_270)
    if orientation is ImageOrientation.ROTATED_180:
        return image.transpose(Image.Transpose.ROTATE_180)
    if orientation is ImageOrientation.ROTATED_270:
        return image.transpose(Image.Transpose.ROTATE_90)
    if orientation is ImageOrientation.MIRRORED:
        return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return image.copy()


def _oriented_size(width: int, height: int, orientation: ImageOrientation) -> tuple[int, int]:
    if orientation in {ImageOrientation.ROTATED_90, ImageOrientation.ROTATED_270}:
        return height, width
    return width, height


def _oriented_region_box(
    region: ImageAnalysisRegion,
    image_width: int,
    image_height: int,
    orientation: ImageOrientation,
) -> tuple[int, int, int, int]:
    x, y, width, height = region.x, region.y, region.width, region.height
    if x + width > image_width or y + height > image_height:
        raise ImageOcrRegionInvalidError()
    if orientation is ImageOrientation.ROTATED_90:
        return image_height - (y + height), x, height, width
    if orientation is ImageOrientation.ROTATED_180:
        return image_width - (x + width), image_height - (y + height), width, height
    if orientation is ImageOrientation.ROTATED_270:
        return y, image_width - (x + width), height, width
    if orientation is ImageOrientation.MIRRORED:
        return image_width - (x + width), y, width, height
    return x, y, width, height
