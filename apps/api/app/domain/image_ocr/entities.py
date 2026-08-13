"""Immutable OCR text evidence and deterministic non-AI assessments."""

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from app.domain.image_ocr.enums import ImageOcrQualityStatus, NameplateTextStatus

WARNING_CODE_MAX_LENGTH = 100
_UNIT_PATTERN = re.compile(
    r"(?i)(?:\b(?:hz|kw|rpm|bar|psi|ip|cos|v|a|w)\b|°c)",
)
_MODEL_PATTERN = re.compile(
    r"\b(?=[A-Za-z0-9-]{3,}\b)(?=[A-Za-z0-9-]*[A-Za-z])(?=[A-Za-z0-9-]*\d)[A-Za-z0-9-]+\b"
)


def _integer(value: int, field: str, *, minimum: int = 0, maximum: int | None = None) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{field} must be an integer of at least {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{field} must be at most {maximum}")


def normalize_ocr_text(value: str) -> str:
    """Normalize unsafe/control whitespace while preserving case, punctuation, and lines."""
    if not isinstance(value, str):
        raise ValueError("OCR text must be a string")
    normalized = value.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.split()) for line in normalized.split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


@dataclass(frozen=True, slots=True, kw_only=True)
class OcrTextBlock:
    block_id: str
    region_id: str
    reading_order: int
    text: str
    confidence_bp: int
    x: int
    y: int
    width: int
    height: int
    relative_x_bp: int
    relative_y_bp: int
    relative_width_bp: int
    relative_height_bp: int

    def __post_init__(self) -> None:
        if not self.block_id.strip() or len(self.block_id) > 50:
            raise ValueError("block_id must be nonempty and bounded")
        if not self.region_id.strip() or len(self.region_id) > 50:
            raise ValueError("region_id must be nonempty and bounded")
        _integer(self.reading_order, "reading_order", minimum=1)
        if not self.text or len(self.text) > 500_000 or self.text != normalize_ocr_text(self.text):
            raise ValueError("text must be nonempty, normalized, and bounded")
        _integer(self.confidence_bp, "confidence_bp", maximum=10_000)
        _integer(self.x, "x")
        _integer(self.y, "y")
        _integer(self.width, "width", minimum=1)
        _integer(self.height, "height", minimum=1)
        for field, value in (
            ("relative_x_bp", self.relative_x_bp),
            ("relative_y_bp", self.relative_y_bp),
            ("relative_width_bp", self.relative_width_bp),
            ("relative_height_bp", self.relative_height_bp),
        ):
            _integer(value, field, maximum=10_000)
        if self.relative_width_bp < 1 or self.relative_height_bp < 1:
            raise ValueError("relative box dimensions must be positive")
        if self.relative_x_bp + self.relative_width_bp > 10_000:
            raise ValueError("relative horizontal box must be bounded")
        if self.relative_y_bp + self.relative_height_bp > 10_000:
            raise ValueError("relative vertical box must be bounded")


def create_ocr_text_block(
    *,
    block_id: str,
    region_id: str,
    reading_order: int,
    text: str,
    confidence_bp: int,
    x: int,
    y: int,
    width: int,
    height: int,
    image_width: int,
    image_height: int,
) -> OcrTextBlock:
    _integer(image_width, "image_width", minimum=1)
    _integer(image_height, "image_height", minimum=1)
    if x + width > image_width or y + height > image_height:
        raise ValueError("OCR box must be inside oriented image bounds")
    x_bp = x * 10_000 // image_width
    y_bp = y * 10_000 // image_height
    right_bp = (x + width) * 10_000 // image_width
    bottom_bp = (y + height) * 10_000 // image_height
    return OcrTextBlock(
        block_id=block_id,
        region_id=region_id,
        reading_order=reading_order,
        text=normalize_ocr_text(text),
        confidence_bp=confidence_bp,
        x=x,
        y=y,
        width=width,
        height=height,
        relative_x_bp=x_bp,
        relative_y_bp=y_bp,
        relative_width_bp=right_bp - x_bp,
        relative_height_bp=bottom_bp - y_bp,
    )


def _overlaps(left: OcrTextBlock, right: OcrTextBlock) -> bool:
    return max(left.x, right.x) < min(left.x + left.width, right.x + right.width) and max(
        left.y, right.y
    ) < min(left.y + left.height, right.y + right.height)


def deduplicate_ocr_blocks(
    blocks: tuple[OcrTextBlock, ...],
) -> tuple[tuple[OcrTextBlock, ...], int]:
    """Suppress only whitespace-normalized exact text with overlapping boxes."""
    retained: list[OcrTextBlock] = []
    duplicate_count = 0
    for block in blocks:
        comparison = " ".join(block.text.split())
        duplicate_index = next(
            (
                index
                for index, existing in enumerate(retained)
                if " ".join(existing.text.split()) == comparison and _overlaps(existing, block)
            ),
            None,
        )
        if duplicate_index is None:
            retained.append(block)
            continue
        duplicate_count += 1
        if block.confidence_bp > retained[duplicate_index].confidence_bp:
            retained[duplicate_index] = block
    retained.sort(key=lambda block: (block.region_id, block.reading_order))
    region_orders: dict[str, int] = {}
    normalized: list[OcrTextBlock] = []
    for index, block in enumerate(retained, start=1):
        region_orders[block.region_id] = region_orders.get(block.region_id, 0) + 1
        normalized.append(
            replace(
                block,
                block_id=f"block-{index:06d}",
                reading_order=region_orders[block.region_id],
            )
        )
    return tuple(normalized), duplicate_count


def assess_ocr_quality(
    blocks: tuple[OcrTextBlock, ...], minimum_confidence_bp: int
) -> ImageOcrQualityStatus:
    _integer(minimum_confidence_bp, "minimum_confidence_bp", maximum=10_000)
    if not blocks:
        return ImageOcrQualityStatus.NO_TEXT
    if any(block.confidence_bp >= minimum_confidence_bp for block in blocks):
        return ImageOcrQualityStatus.TEXT_FOUND
    return ImageOcrQualityStatus.LOW_CONFIDENCE_TEXT


def assess_nameplate_text(
    blocks: tuple[OcrTextBlock, ...],
) -> tuple[NameplateTextStatus, int]:
    if not blocks:
        return NameplateTextStatus.NO_TEXT, 0
    lines = [line for block in blocks for line in block.text.splitlines() if line]
    digit_lines = sum(any(character.isdigit() for character in line) for line in lines)
    text = "\n".join(lines)
    score = 20 if len(lines) >= 2 else 0
    score += 25 if digit_lines * 2 >= len(lines) else 0
    score += 25 if _UNIT_PATTERN.search(text) else 0
    score += 20 if any(":" in line for line in lines) else 0
    score += 10 if _MODEL_PATTERN.search(text) else 0
    if score >= 50:
        return NameplateTextStatus.LIKELY_NAMEPLATE_TEXT, score
    if score <= 20:
        return NameplateTextStatus.GENERIC_TEXT, score
    return NameplateTextStatus.UNKNOWN, score


@dataclass(frozen=True, slots=True, kw_only=True)
class ImageOcrResult:
    ocr_id: UUID
    job_id: UUID
    product_id: UUID
    source_id: UUID
    image_analysis_id: UUID
    engine: str
    engine_version: str
    image_width: int
    image_height: int
    region_count: int
    block_count: int
    duplicate_block_count: int
    total_character_count: int
    average_confidence_bp: int
    quality_status: ImageOcrQualityStatus
    nameplate_text_status: NameplateTextStatus
    nameplate_heuristic_score: int
    blocks: tuple[OcrTextBlock, ...]
    warning_codes: tuple[str, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, UUID)
            for value in (
                self.ocr_id,
                self.job_id,
                self.product_id,
                self.source_id,
                self.image_analysis_id,
            )
        ):
            raise ValueError("OCR result identities must be UUIDs")
        if not self.engine.strip() or len(self.engine) > 100:
            raise ValueError("engine must be nonempty and bounded")
        if not self.engine_version.strip() or len(self.engine_version) > 100:
            raise ValueError("engine_version must be nonempty and bounded")
        _integer(self.image_width, "image_width", minimum=1)
        _integer(self.image_height, "image_height", minimum=1)
        _integer(self.region_count, "region_count", minimum=1)
        _integer(self.block_count, "block_count")
        _integer(self.duplicate_block_count, "duplicate_block_count")
        if self.block_count != len(self.blocks):
            raise ValueError("block_count must match blocks")
        if self.total_character_count != sum(len(block.text) for block in self.blocks):
            raise ValueError("total_character_count must match blocks")
        _integer(self.total_character_count, "total_character_count")
        expected_average = (
            sum(block.confidence_bp for block in self.blocks) // len(self.blocks)
            if self.blocks
            else 0
        )
        if self.average_confidence_bp != expected_average:
            raise ValueError("average_confidence_bp must match blocks")
        _integer(self.average_confidence_bp, "average_confidence_bp", maximum=10_000)
        if not isinstance(self.quality_status, ImageOcrQualityStatus):
            raise ValueError("quality_status must be an ImageOcrQualityStatus")
        _integer(self.nameplate_heuristic_score, "nameplate_heuristic_score", maximum=100)
        expected_status, expected_score = assess_nameplate_text(self.blocks)
        if (
            self.nameplate_text_status is not expected_status
            or self.nameplate_heuristic_score != expected_score
        ):
            raise ValueError("nameplate assessment must match deterministic text heuristic")
        for block in self.blocks:
            if (
                block.x + block.width > self.image_width
                or block.y + block.height > self.image_height
            ):
                raise ValueError("OCR block must be inside oriented image bounds")
        if tuple(block.block_id for block in self.blocks) != tuple(
            f"block-{index:06d}" for index in range(1, len(self.blocks) + 1)
        ):
            raise ValueError("OCR block identities must be deterministic")
        region_orders: dict[str, int] = {}
        for block in self.blocks:
            region_orders[block.region_id] = region_orders.get(block.region_id, 0) + 1
            if block.reading_order != region_orders[block.region_id]:
                raise ValueError("OCR reading order must be contiguous within each region")
        if len(set(self.warning_codes)) != len(self.warning_codes) or any(
            not code.strip() or len(code) > WARNING_CODE_MAX_LENGTH for code in self.warning_codes
        ):
            raise ValueError("warning codes must be unique, nonempty, and bounded")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "engine", self.engine.strip())
        object.__setattr__(self, "engine_version", self.engine_version.strip())
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))

    @classmethod
    def create(
        cls,
        *,
        job_id: UUID,
        product_id: UUID,
        source_id: UUID,
        image_analysis_id: UUID,
        engine: str,
        engine_version: str,
        image_width: int,
        image_height: int,
        region_count: int,
        blocks: tuple[OcrTextBlock, ...],
        duplicate_block_count: int,
        minimum_confidence_bp: int,
        now: datetime | None = None,
    ) -> Self:
        quality = assess_ocr_quality(blocks, minimum_confidence_bp)
        nameplate_status, score = assess_nameplate_text(blocks)
        return cls(
            ocr_id=uuid4(),
            job_id=job_id,
            product_id=product_id,
            source_id=source_id,
            image_analysis_id=image_analysis_id,
            engine=engine,
            engine_version=engine_version,
            image_width=image_width,
            image_height=image_height,
            region_count=region_count,
            block_count=len(blocks),
            duplicate_block_count=duplicate_block_count,
            total_character_count=sum(len(block.text) for block in blocks),
            average_confidence_bp=(
                sum(block.confidence_bp for block in blocks) // len(blocks) if blocks else 0
            ),
            quality_status=quality,
            nameplate_text_status=nameplate_status,
            nameplate_heuristic_score=score,
            blocks=blocks,
            warning_codes=(),
            created_at=now or datetime.now(UTC),
        )
