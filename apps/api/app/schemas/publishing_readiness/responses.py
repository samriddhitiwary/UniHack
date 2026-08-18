"""Publishing-readiness application and inspection response schemas."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.catalog_projection import (
    CatalogBlockingReason,
    CatalogProjectionStatus,
    CatalogWarningReason,
)
from app.domain.products import ProductStatus
from app.schemas.products.models import to_camel


class PublishingReadinessSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class PublishingReadinessApplicationResponse(PublishingReadinessSchema):
    product_id: UUID
    projection_id: UUID
    projection_status: CatalogProjectionStatus
    previous_status: ProductStatus
    status: ProductStatus
    previous_version: int = Field(gt=0)
    version: int = Field(gt=0)
    applied_at: AwareDatetime
    warning_reason_codes: tuple[CatalogWarningReason, ...]


class CatalogPublishingReadinessResponse(PublishingReadinessSchema):
    product_id: UUID
    projection_id: UUID
    projection_status: CatalogProjectionStatus
    blocking_reason_codes: tuple[CatalogBlockingReason, ...]
    warning_reason_codes: tuple[CatalogWarningReason, ...]
    product_version_at_projection: int = Field(gt=0)
    current_product_version: int = Field(gt=0)
    projection_current: bool
    eligible_for_ready_to_publish: bool
    current_product_status: ProductStatus
