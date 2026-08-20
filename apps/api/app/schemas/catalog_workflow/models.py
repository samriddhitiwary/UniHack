"""Strict camelCase Catalog Intelligence workflow API models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.catalog_workflow import (
    CatalogIntelligenceWorkflow,
    CatalogWorkflowHistoryPage,
    CatalogWorkflowNextAction,
    CatalogWorkflowStageName,
    CatalogWorkflowStageStatus,
    CatalogWorkflowStatus,
)
from app.schemas.products.models import to_camel


class CatalogWorkflowSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        from_attributes=True,
        extra="forbid",
    )


class CatalogWorkflowConfigurationRequest(CatalogWorkflowSchema):
    apply_publishing_readiness: bool = True
    generate_export: bool = True
    generate_ai_enrichment: bool = True
    calculate_intelligence_score: bool = True
    fail_on_optional_stage_error: bool = False


class CatalogWorkflowResumeRequest(CatalogWorkflowSchema):
    version: int = Field(ge=1, strict=True)


class CatalogWorkflowStageResponse(CatalogWorkflowSchema):
    stage: CatalogWorkflowStageName
    status: CatalogWorkflowStageStatus
    job_id: UUID | None
    child_job_ids: tuple[UUID, ...]
    result_reference: str | None
    started_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None
    skip_reason: str | None


class CatalogWorkflowResponse(CatalogWorkflowSchema):
    workflow_id: UUID
    product_id: UUID
    status: CatalogWorkflowStatus
    version: int
    product_version: int
    current_stage: CatalogWorkflowStageName | None
    progress_percent: int
    stages: tuple[CatalogWorkflowStageResponse, ...]
    review_id: UUID | None
    projection_id: UUID | None
    export_id: UUID | None
    enrichment_id: UUID | None
    score_id: UUID | None
    next_action: CatalogWorkflowNextAction
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None

    @classmethod
    def from_domain(cls, workflow: CatalogIntelligenceWorkflow) -> "CatalogWorkflowResponse":
        return cls(
            **{
                field: getattr(workflow, field)
                for field in cls.model_fields
                if field not in {"next_action"}
            },
            next_action=workflow.next_action,
        )


class CatalogWorkflowHistoryItemResponse(CatalogWorkflowSchema):
    workflow_id: UUID
    product_id: UUID
    status: CatalogWorkflowStatus
    progress_percent: int
    current_stage: CatalogWorkflowStageName | None
    created_at: datetime
    completed_at: datetime | None


class CatalogWorkflowHistoryResponse(CatalogWorkflowSchema):
    items: tuple[CatalogWorkflowHistoryItemResponse, ...]
    next_cursor: str | None

    @classmethod
    def from_domain(cls, page: CatalogWorkflowHistoryPage) -> "CatalogWorkflowHistoryResponse":
        return cls(
            items=tuple(
                CatalogWorkflowHistoryItemResponse.model_validate(item) for item in page.items
            ),
            next_cursor=page.next_cursor,
        )
