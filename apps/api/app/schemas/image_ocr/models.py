"""Internal schemas for image OCR evidence records."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.image_ocr import ImageOcrQualityStatus, NameplateTextStatus
from app.schemas.products.models import to_camel


class ImageOcrSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class OcrTextBlockRecord(ImageOcrSchema):
    block_id: str
    region_id: str
    reading_order: int = Field(ge=1)
    text: str
    confidence_bp: int = Field(ge=0, le=10_000)
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    relative_x_bp: int = Field(ge=0, le=10_000)
    relative_y_bp: int = Field(ge=0, le=10_000)
    relative_width_bp: int = Field(ge=1, le=10_000)
    relative_height_bp: int = Field(ge=1, le=10_000)


class ImageOcrResultRecord(ImageOcrSchema):
    ocr_id: UUID
    job_id: UUID
    product_id: UUID
    source_id: UUID
    image_analysis_id: UUID
    engine: str
    engine_version: str
    image_width: int = Field(ge=1)
    image_height: int = Field(ge=1)
    region_count: int = Field(ge=1)
    block_count: int = Field(ge=0)
    duplicate_block_count: int = Field(ge=0)
    total_character_count: int = Field(ge=0)
    average_confidence_bp: int = Field(ge=0, le=10_000)
    quality_status: ImageOcrQualityStatus
    nameplate_text_status: NameplateTextStatus
    nameplate_heuristic_score: int = Field(ge=0, le=100)
    blocks: list[OcrTextBlockRecord]
    warning_codes: list[str]
    created_at: datetime
