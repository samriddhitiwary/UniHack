"""Internal schemas for CSV processing records."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.csv_processing import CsvProcessingQualityStatus
from app.schemas.products.models import to_camel


class CsvProcessingSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class CsvHeaderCellRecord(CsvProcessingSchema):
    column_index: int = Field(ge=0)
    text: str
    is_empty: bool


class CsvCellRecord(CsvProcessingSchema):
    column_index: int = Field(ge=0)
    text: str
    is_empty: bool


class CsvRowRecord(CsvProcessingSchema):
    row_number: int = Field(ge=1)
    cells: list[CsvCellRecord]
    extra_cells: list[CsvCellRecord]
    original_column_count: int = Field(ge=0)
    normalized_column_count: int = Field(ge=1)
    is_malformed: bool
    warning_codes: list[str]


class CsvProcessingResultRecord(CsvProcessingSchema):
    processing_id: UUID
    job_id: UUID
    product_id: UUID
    source_id: UUID
    encoding: str
    delimiter: str
    header: list[CsvHeaderCellRecord]
    column_count: int = Field(ge=1)
    row_count: int = Field(ge=0)
    malformed_row_count: int = Field(ge=0)
    empty_cell_count: int = Field(ge=0)
    total_cell_count: int = Field(ge=0)
    quality_status: CsvProcessingQualityStatus
    rows: list[CsvRowRecord]
    warning_codes: list[str]
    created_at: datetime
