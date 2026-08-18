"""Publishing-readiness command schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.products.models import to_camel


class ApplyPublishingReadinessRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
    )

    projection_id: UUID
    version: int = Field(ge=1, strict=True)
