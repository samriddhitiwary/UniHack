"""Internal safe schemas for PDF text-extraction results."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.pdf_extraction import PdfExtractionQualityStatus
from app.schemas.products.models import to_camel


class PdfExtractionSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class PdfExtractionPageRecord(PdfExtractionSchema):
    page_number: int = Field(ge=1)
    text: str
    character_count: int = Field(ge=0)
    has_text: bool


class PdfTextExtractionResultRecord(PdfExtractionSchema):
    extraction_id: UUID
    job_id: UUID
    product_id: UUID
    source_id: UUID
    parser: str
    parser_version: str
    page_count: int = Field(ge=1)
    pages_with_text: int = Field(ge=0)
    total_character_count: int = Field(ge=0)
    quality_status: PdfExtractionQualityStatus
    pages: list[PdfExtractionPageRecord]
    warning_codes: list[str]
    created_at: datetime
