"""Internal schemas for PDF table-extraction records."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.pdf_table_extraction import PdfTableExtractionQualityStatus
from app.schemas.products.models import to_camel


class PdfTableSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class PdfTableCellRecord(PdfTableSchema):
    row_index: int = Field(ge=0)
    column_index: int = Field(ge=0)
    text: str
    is_empty: bool


class PdfTableRowRecord(PdfTableSchema):
    row_index: int = Field(ge=0)
    cells: list[PdfTableCellRecord]


class PdfExtractedTableRecord(PdfTableSchema):
    table_index: int = Field(ge=1)
    page_number: int = Field(ge=1)
    row_count: int = Field(ge=1)
    column_count: int = Field(ge=1)
    cell_count: int = Field(ge=1)
    rows: list[PdfTableRowRecord]


class PdfTableExtractionResultRecord(PdfTableSchema):
    extraction_id: UUID
    job_id: UUID
    product_id: UUID
    source_id: UUID
    parser: str
    parser_version: str
    page_count: int = Field(ge=1)
    pages_with_tables: int = Field(ge=0)
    table_count: int = Field(ge=0)
    total_row_count: int = Field(ge=0)
    total_cell_count: int = Field(ge=0)
    quality_status: PdfTableExtractionQualityStatus
    tables: list[PdfExtractedTableRecord]
    warning_codes: list[str]
    created_at: datetime
