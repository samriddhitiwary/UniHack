"""Strict internal schemas for immutable catalog export results."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.catalog_export import CatalogExportArtifactFormat, CatalogExportStatus
from app.domain.catalog_projection import CatalogProjectionStatus, CatalogWarningReason
from app.domain.products import ProductCategory
from app.schemas.products.models import to_camel


class CatalogExportSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class CatalogExportArtifactRecord(CatalogExportSchema):
    format: CatalogExportArtifactFormat
    file_name: str
    media_type: str
    object_key: str
    size_bytes: int = Field(gt=0)
    sha256: str = Field(min_length=64, max_length=64)
    created_at: AwareDatetime


class CatalogExportResultRecord(CatalogExportSchema):
    export_id: UUID
    job_id: UUID
    product_id: UUID
    projection_id: UUID
    projection_product_version: int = Field(gt=0)
    category: ProductCategory
    schema_version: int = Field(gt=0)
    schema_fingerprint: str = Field(min_length=64, max_length=64)
    projection_status: CatalogProjectionStatus
    status: CatalogExportStatus
    artifacts: tuple[CatalogExportArtifactRecord, ...]
    warning_reason_codes: tuple[CatalogWarningReason, ...]
    engine: str
    engine_version: str
    created_at: AwareDatetime
