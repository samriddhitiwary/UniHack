"""Image OCR evidence domain."""

from app.domain.image_ocr.entities import (
    ImageOcrResult,
    OcrTextBlock,
    assess_nameplate_text,
    assess_ocr_quality,
    create_ocr_text_block,
    deduplicate_ocr_blocks,
    normalize_ocr_text,
)
from app.domain.image_ocr.enums import ImageOcrQualityStatus, NameplateTextStatus

__all__ = [
    "ImageOcrQualityStatus",
    "ImageOcrResult",
    "NameplateTextStatus",
    "OcrTextBlock",
    "assess_nameplate_text",
    "assess_ocr_quality",
    "create_ocr_text_block",
    "deduplicate_ocr_blocks",
    "normalize_ocr_text",
]
