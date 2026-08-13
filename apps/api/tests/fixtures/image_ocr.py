"""Deterministic OCR evidence fixtures."""

from datetime import UTC, datetime
from uuid import UUID

from app.domain.image_ocr import ImageOcrResult, OcrTextBlock, create_ocr_text_block
from tests.fixtures.image_analysis import ANALYSIS_ID
from tests.fixtures.processing_jobs import SECOND_JOB_ID
from tests.fixtures.product_sources import SOURCE_ID
from tests.fixtures.products import PRODUCT_ID

OCR_ID = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
OCR_CREATED_AT = datetime(2026, 8, 12, 8, 0, tzinfo=UTC)


def make_ocr_block(
    *,
    block_id: str = "block-000001",
    region_id: str = "region-000001",
    reading_order: int = 1,
    text: str = "MOTOR 415 V",
    confidence_bp: int = 9_000,
    x: int = 10,
    y: int = 20,
    width: int = 100,
    height: int = 20,
    image_width: int = 400,
    image_height: int = 200,
) -> OcrTextBlock:
    return create_ocr_text_block(
        block_id=block_id,
        region_id=region_id,
        reading_order=reading_order,
        text=text,
        confidence_bp=confidence_bp,
        x=x,
        y=y,
        width=width,
        height=height,
        image_width=image_width,
        image_height=image_height,
    )


def make_image_ocr_result(
    *,
    ocr_id: UUID = OCR_ID,
    blocks: tuple[OcrTextBlock, ...] | None = None,
    region_count: int = 2,
    duplicate_block_count: int = 0,
    minimum_confidence_bp: int = 4_000,
) -> ImageOcrResult:
    evidence = blocks if blocks is not None else (make_ocr_block(),)
    created = ImageOcrResult.create(
        job_id=SECOND_JOB_ID,
        product_id=PRODUCT_ID,
        source_id=SOURCE_ID,
        image_analysis_id=ANALYSIS_ID,
        engine="RapidOCR-ONNXRuntime",
        engine_version="1.4.4",
        image_width=400,
        image_height=200,
        region_count=region_count,
        blocks=evidence,
        duplicate_block_count=duplicate_block_count,
        minimum_confidence_bp=minimum_confidence_bp,
        now=OCR_CREATED_AT,
    )
    return ImageOcrResult(
        ocr_id=ocr_id,
        job_id=created.job_id,
        product_id=created.product_id,
        source_id=created.source_id,
        image_analysis_id=created.image_analysis_id,
        engine=created.engine,
        engine_version=created.engine_version,
        image_width=created.image_width,
        image_height=created.image_height,
        region_count=created.region_count,
        block_count=created.block_count,
        duplicate_block_count=created.duplicate_block_count,
        total_character_count=created.total_character_count,
        average_confidence_bp=created.average_confidence_bp,
        quality_status=created.quality_status,
        nameplate_text_status=created.nameplate_text_status,
        nameplate_heuristic_score=created.nameplate_heuristic_score,
        blocks=created.blocks,
        warning_codes=created.warning_codes,
        created_at=created.created_at,
    )
