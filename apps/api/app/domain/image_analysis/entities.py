"""Immutable privacy-safe image metadata and deterministic region evidence."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from app.domain.image_analysis.enums import (
    ImageOrientation,
    ImageRegionType,
    NameplateCandidateStatus,
)

REGION_ORDER = tuple(ImageRegionType)
WARNING_CODE_MAX_LENGTH = 100


def _positive(value: int, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")


@dataclass(frozen=True, slots=True, kw_only=True)
class ImageMetadata:
    format: str
    mime_type: str
    width: int
    height: int
    pixel_count: int
    aspect_ratio_numerator: int
    aspect_ratio_denominator: int
    color_mode: str
    has_alpha: bool
    is_grayscale: bool
    orientation: ImageOrientation
    file_size_bytes: int

    def __post_init__(self) -> None:
        if self.format not in {"PNG", "JPEG", "WEBP"}:
            raise ValueError("format must be supported")
        expected_mime = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}[
            self.format
        ]
        if self.mime_type != expected_mime:
            raise ValueError("mime_type must match format")
        for field, value in (
            ("width", self.width),
            ("height", self.height),
            ("file_size_bytes", self.file_size_bytes),
        ):
            _positive(value, field)
        if self.pixel_count != self.width * self.height:
            raise ValueError("pixel_count must equal width times height")
        if (
            self.aspect_ratio_numerator != self.width
            or self.aspect_ratio_denominator != self.height
        ):
            raise ValueError("aspect representation must preserve width and height")
        if not self.color_mode.strip() or len(self.color_mode) > 20:
            raise ValueError("color_mode must be nonempty and bounded")
        if not isinstance(self.orientation, ImageOrientation):
            raise ValueError("orientation must be an ImageOrientation")


@dataclass(frozen=True, slots=True, kw_only=True)
class ImageAnalysisRegion:
    region_id: str
    region_type: ImageRegionType
    x: int
    y: int
    width: int
    height: int
    relative_x_bp: int
    relative_y_bp: int
    relative_width_bp: int
    relative_height_bp: int
    heuristic_score: int

    def __post_init__(self) -> None:
        if not self.region_id.strip() or len(self.region_id) > 50:
            raise ValueError("region_id must be nonempty and bounded")
        for field, value in (("x", self.x), ("y", self.y)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field} must be a non-negative integer")
        _positive(self.width, "width")
        _positive(self.height, "height")
        for field, value in (
            ("relative_x_bp", self.relative_x_bp),
            ("relative_y_bp", self.relative_y_bp),
            ("relative_width_bp", self.relative_width_bp),
            ("relative_height_bp", self.relative_height_bp),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 10_000:
                raise ValueError(f"{field} must be basis points from zero to 10000")
        if self.relative_width_bp < 1 or self.relative_height_bp < 1:
            raise ValueError("relative region dimensions must be positive")
        if self.relative_x_bp + self.relative_width_bp > 10_000:
            raise ValueError("relative horizontal region must be bounded")
        if self.relative_y_bp + self.relative_height_bp > 10_000:
            raise ValueError("relative vertical region must be bounded")
        if isinstance(self.heuristic_score, bool) or not 0 <= self.heuristic_score <= 100:
            raise ValueError("heuristic_score must be between zero and 100")


def assess_nameplate_candidate(width: int, height: int) -> tuple[NameplateCandidateStatus, int]:
    _positive(width, "width")
    _positive(height, "height")
    score = (40 if width >= 300 else 0) + (30 if height >= 150 else 0)
    if width * 2 >= height and width <= height * 4:
        score += 30
    if width < 150 or height < 75 or width * 4 < height or width > height * 8:
        return NameplateCandidateStatus.UNLIKELY, score
    if width >= 300 and height >= 150 and width * 2 >= height and width <= height * 4:
        return NameplateCandidateStatus.POSSIBLE, score
    return NameplateCandidateStatus.UNKNOWN, score


def generate_analysis_regions(
    width: int, height: int, heuristic_score: int
) -> tuple[ImageAnalysisRegion, ...]:
    _positive(width, "width")
    _positive(height, "height")
    half_width = max(1, (width + 1) // 2)
    half_height = max(1, (height + 1) // 2)
    boxes = (
        (ImageRegionType.FULL_IMAGE, 0, 0, width, height),
        (
            ImageRegionType.CENTER,
            (width - half_width) // 2,
            (height - half_height) // 2,
            half_width,
            half_height,
        ),
        (ImageRegionType.TOP, 0, 0, width, half_height),
        (ImageRegionType.BOTTOM, 0, height - half_height, width, half_height),
        (ImageRegionType.LEFT, 0, 0, half_width, height),
        (ImageRegionType.RIGHT, width - half_width, 0, half_width, height),
    )
    return tuple(
        _region(index, region_type, x, y, box_width, box_height, width, height, heuristic_score)
        for index, (region_type, x, y, box_width, box_height) in enumerate(boxes, start=1)
    )


def _region(
    index: int,
    region_type: ImageRegionType,
    x: int,
    y: int,
    width: int,
    height: int,
    image_width: int,
    image_height: int,
    score: int,
) -> ImageAnalysisRegion:
    x_bp = x * 10_000 // image_width
    y_bp = y * 10_000 // image_height
    right_bp = (x + width) * 10_000 // image_width
    bottom_bp = (y + height) * 10_000 // image_height
    return ImageAnalysisRegion(
        region_id=f"region-{index:06d}",
        region_type=region_type,
        x=x,
        y=y,
        width=width,
        height=height,
        relative_x_bp=x_bp,
        relative_y_bp=y_bp,
        relative_width_bp=right_bp - x_bp,
        relative_height_bp=bottom_bp - y_bp,
        heuristic_score=score,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ImageAnalysisResult:
    analysis_id: UUID
    job_id: UUID
    product_id: UUID
    source_id: UUID
    parser: str
    parser_version: str
    metadata: ImageMetadata
    nameplate_candidate_status: NameplateCandidateStatus
    heuristic_score: int
    regions: tuple[ImageAnalysisRegion, ...]
    warning_codes: tuple[str, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, UUID)
            for value in (self.analysis_id, self.job_id, self.product_id, self.source_id)
        ):
            raise ValueError("result identities must be UUIDs")
        if not self.parser.strip() or len(self.parser) > 50:
            raise ValueError("parser must be nonempty and bounded")
        if not self.parser_version.strip() or len(self.parser_version) > 50:
            raise ValueError("parser_version must be nonempty and bounded")
        expected_status, expected_score = assess_nameplate_candidate(
            self.metadata.width, self.metadata.height
        )
        if (
            self.nameplate_candidate_status is not expected_status
            or self.heuristic_score != expected_score
        ):
            raise ValueError("candidate assessment must match deterministic metadata heuristic")
        if tuple(region.region_type for region in self.regions) != REGION_ORDER:
            raise ValueError("regions must use the deterministic complete order")
        if tuple(region.region_id for region in self.regions) != tuple(
            f"region-{index:06d}" for index in range(1, len(REGION_ORDER) + 1)
        ):
            raise ValueError("region identities must be deterministic")
        for region in self.regions:
            if (
                region.x + region.width > self.metadata.width
                or region.y + region.height > self.metadata.height
            ):
                raise ValueError("region must be inside image bounds")
            if region.heuristic_score != self.heuristic_score:
                raise ValueError("region score must match result heuristic score")
        if len(set(self.warning_codes)) != len(self.warning_codes) or any(
            not code.strip() or len(code) > WARNING_CODE_MAX_LENGTH for code in self.warning_codes
        ):
            raise ValueError("warning codes must be unique, nonempty, and bounded")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "parser", self.parser.strip())
        object.__setattr__(self, "parser_version", self.parser_version.strip())
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))

    @classmethod
    def create(
        cls,
        *,
        job_id: UUID,
        product_id: UUID,
        source_id: UUID,
        parser: str,
        parser_version: str,
        metadata: ImageMetadata,
        regions: tuple[ImageAnalysisRegion, ...],
        now: datetime | None = None,
    ) -> Self:
        status, score = assess_nameplate_candidate(metadata.width, metadata.height)
        return cls(
            analysis_id=uuid4(),
            job_id=job_id,
            product_id=product_id,
            source_id=source_id,
            parser=parser,
            parser_version=parser_version,
            metadata=metadata,
            nameplate_candidate_status=status,
            heuristic_score=score,
            regions=regions,
            warning_codes=(),
            created_at=now or datetime.now(UTC),
        )
