"""Internal schemas for image-analysis records."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.image_analysis import ImageOrientation, ImageRegionType, NameplateCandidateStatus
from app.schemas.products.models import to_camel


class ImageAnalysisSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ImageMetadataRecord(ImageAnalysisSchema):
    format: str
    mime_type: str
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    pixel_count: int = Field(ge=1)
    aspect_ratio_numerator: int = Field(ge=1)
    aspect_ratio_denominator: int = Field(ge=1)
    color_mode: str
    has_alpha: bool
    is_grayscale: bool
    orientation: ImageOrientation
    file_size_bytes: int = Field(ge=1)


class ImageAnalysisRegionRecord(ImageAnalysisSchema):
    region_id: str
    region_type: ImageRegionType
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    relative_x_bp: int = Field(ge=0, le=10_000)
    relative_y_bp: int = Field(ge=0, le=10_000)
    relative_width_bp: int = Field(ge=1, le=10_000)
    relative_height_bp: int = Field(ge=1, le=10_000)
    heuristic_score: int = Field(ge=0, le=100)


class ImageAnalysisResultRecord(ImageAnalysisSchema):
    analysis_id: UUID
    job_id: UUID
    product_id: UUID
    source_id: UUID
    parser: str
    parser_version: str
    metadata: ImageMetadataRecord
    nameplate_candidate_status: NameplateCandidateStatus
    heuristic_score: int = Field(ge=0, le=100)
    regions: list[ImageAnalysisRegionRecord]
    warning_codes: list[str]
    created_at: datetime
