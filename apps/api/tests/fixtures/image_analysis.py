"""Generated image bytes and deterministic image-analysis domain fixtures."""

from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID

from PIL import Image

from app.domain.image_analysis import (
    ImageAnalysisResult,
    ImageMetadata,
    ImageOrientation,
    assess_nameplate_candidate,
    generate_analysis_regions,
)
from tests.fixtures.processing_jobs import JOB_ID
from tests.fixtures.product_sources import SOURCE_ID
from tests.fixtures.products import PRODUCT_ID

ANALYSIS_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
ANALYSIS_CREATED_AT = datetime(2026, 8, 12, 7, 0, tzinfo=UTC)


def make_image_bytes(
    format: str = "PNG",
    *,
    size: tuple[int, int] = (400, 200),
    mode: str = "RGB",
    orientation: int | None = None,
    animated: bool = False,
) -> bytes:
    output = BytesIO()
    image = Image.new(
        mode,
        size,
        128 if mode in {"1", "L"} else (10, 20, 30, 128) if "A" in mode else (10, 20, 30),
    )
    kwargs: dict[str, object] = {}
    if orientation is not None:
        exif = Image.Exif()
        exif[274] = orientation
        kwargs["exif"] = exif
    if animated:
        second = Image.new(mode, size, 64 if mode in {"1", "L"} else (30, 20, 10))
        kwargs.update(save_all=True, append_images=[second], duration=100, loop=0)
    image.save(output, format=format, **kwargs)
    return output.getvalue()


def make_image_analysis_result(
    *, analysis_id: UUID = ANALYSIS_ID, width: int = 400, height: int = 200
) -> ImageAnalysisResult:
    metadata = ImageMetadata(
        format="PNG",
        mime_type="image/png",
        width=width,
        height=height,
        pixel_count=width * height,
        aspect_ratio_numerator=width,
        aspect_ratio_denominator=height,
        color_mode="RGB",
        has_alpha=False,
        is_grayscale=False,
        orientation=ImageOrientation.NORMAL,
        file_size_bytes=100,
    )
    _, score = assess_nameplate_candidate(width, height)
    created = ImageAnalysisResult.create(
        job_id=JOB_ID,
        product_id=PRODUCT_ID,
        source_id=SOURCE_ID,
        parser="Pillow",
        parser_version="12.1.0",
        metadata=metadata,
        regions=generate_analysis_regions(width, height, score),
        now=ANALYSIS_CREATED_AT,
    )
    return ImageAnalysisResult(
        analysis_id=analysis_id,
        job_id=created.job_id,
        product_id=created.product_id,
        source_id=created.source_id,
        parser=created.parser,
        parser_version=created.parser_version,
        metadata=created.metadata,
        nameplate_candidate_status=created.nameplate_candidate_status,
        heuristic_score=created.heuristic_score,
        regions=created.regions,
        warning_codes=created.warning_codes,
        created_at=created.created_at,
    )
