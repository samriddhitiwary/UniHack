"""Immutable Catalog Intelligence workflow state and compact history models."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.domain.catalog_workflow.enums import (
    TERMINAL_STAGE_STATUSES,
    TERMINAL_WORKFLOW_STATUSES,
    CatalogWorkflowNextAction,
    CatalogWorkflowStageName,
    CatalogWorkflowStageStatus,
    CatalogWorkflowStatus,
)
from app.domain.product_sources import ProductSourceType


def _utc(value: datetime | None, field: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogIntelligenceWorkflowConfiguration:
    apply_publishing_readiness: bool = True
    generate_export: bool = True
    generate_ai_enrichment: bool = True
    calculate_intelligence_score: bool = True
    fail_on_optional_stage_error: bool = False

    def __post_init__(self) -> None:
        if not all(
            isinstance(value, bool)
            for value in (
                self.apply_publishing_readiness,
                self.generate_export,
                self.generate_ai_enrichment,
                self.calculate_intelligence_score,
                self.fail_on_optional_stage_error,
            )
        ):
            raise ValueError("workflow configuration values must be booleans")


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogWorkflowSourceSnapshot:
    source_id: UUID
    source_type: ProductSourceType

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, UUID) or not isinstance(
            self.source_type, ProductSourceType
        ):
            raise ValueError("workflow source snapshot is invalid")


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogIntelligenceWorkflowStage:
    stage: CatalogWorkflowStageName
    status: CatalogWorkflowStageStatus = CatalogWorkflowStageStatus.NOT_STARTED
    job_id: UUID | None = None
    child_job_ids: tuple[UUID, ...] = ()
    result_reference: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
    skip_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.stage, CatalogWorkflowStageName) or not isinstance(
            self.status, CatalogWorkflowStageStatus
        ):
            raise ValueError("workflow stage identity/status is invalid")
        if self.job_id is not None and not isinstance(self.job_id, UUID):
            raise ValueError("workflow stage job_id is invalid")
        if len(self.child_job_ids) > 200 or any(
            not isinstance(value, UUID) for value in self.child_job_ids
        ):
            raise ValueError("workflow child jobs are invalid")
        started = _utc(self.started_at, "started_at")
        completed = _utc(self.completed_at, "completed_at")
        if completed is not None and started is None:
            raise ValueError("completed workflow stage must have started")
        if completed is not None and started is not None and completed < started:
            raise ValueError("workflow stage completion precedes start")
        if self.status is CatalogWorkflowStageStatus.NOT_STARTED and any(
            value is not None for value in (started, completed, self.error_code, self.skip_reason)
        ):
            raise ValueError("unstarted workflow stage contains activity")
        if self.status in TERMINAL_STAGE_STATUSES and completed is None:
            raise ValueError("terminal workflow stage requires completion time")
        if (
            self.status
            in {
                CatalogWorkflowStageStatus.RUNNING,
                CatalogWorkflowStageStatus.WAITING,
            }
            and started is None
        ):
            raise ValueError("active workflow stage requires start time")
        if self.status is CatalogWorkflowStageStatus.SKIPPED and not self.skip_reason:
            raise ValueError("skipped workflow stage requires a reason")
        if self.status is CatalogWorkflowStageStatus.FAILED and not self.error_code:
            raise ValueError("failed workflow stage requires an error code")
        for value, maximum in (
            (self.result_reference, 1_024),
            (self.error_code, 100),
            (self.error_message, 2_000),
            (self.skip_reason, 100),
        ):
            if value is not None and (not value.strip() or len(value) > maximum):
                raise ValueError("workflow stage text is invalid")
        object.__setattr__(self, "started_at", started)
        object.__setattr__(self, "completed_at", completed)


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogWorkflowStageOutcome:
    status: CatalogWorkflowStageStatus
    job_id: UUID | None = None
    child_job_ids: tuple[UUID, ...] = ()
    result_reference: str | None = None
    skip_reason: str | None = None
    classification_id: UUID | None = None
    extraction_id: UUID | None = None
    normalization_id: UUID | None = None
    conflict_detection_id: UUID | None = None
    completeness_id: UUID | None = None
    validation_id: UUID | None = None
    selection_id: UUID | None = None
    review_id: UUID | None = None
    materialization_id: UUID | None = None
    projection_id: UUID | None = None
    export_id: UUID | None = None
    enrichment_id: UUID | None = None
    score_id: UUID | None = None
    product_version: int | None = None

    def __post_init__(self) -> None:
        if self.status not in {
            CatalogWorkflowStageStatus.COMPLETED,
            CatalogWorkflowStageStatus.SKIPPED,
            CatalogWorkflowStageStatus.WAITING,
        }:
            raise ValueError("stage outcome must complete, skip, or wait")
        if self.status is CatalogWorkflowStageStatus.SKIPPED and not self.skip_reason:
            raise ValueError("skipped outcome requires reason")
        if self.status is CatalogWorkflowStageStatus.WAITING and self.review_id is None:
            raise ValueError("waiting outcome requires review_id")


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogIntelligenceWorkflow:
    workflow_id: UUID
    product_id: UUID
    status: CatalogWorkflowStatus
    version: int
    product_version: int
    configuration: CatalogIntelligenceWorkflowConfiguration
    source_snapshot: tuple[CatalogWorkflowSourceSnapshot, ...]
    current_stage: CatalogWorkflowStageName | None
    progress_percent: int
    stages: tuple[CatalogIntelligenceWorkflowStage, ...]
    classification_id: UUID | None = None
    extraction_id: UUID | None = None
    normalization_id: UUID | None = None
    conflict_detection_id: UUID | None = None
    completeness_id: UUID | None = None
    validation_id: UUID | None = None
    selection_id: UUID | None = None
    review_id: UUID | None = None
    materialization_id: UUID | None = None
    projection_id: UUID | None = None
    export_id: UUID | None = None
    enrichment_id: UUID | None = None
    score_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.workflow_id, UUID) or not isinstance(self.product_id, UUID):
            raise ValueError("workflow identifiers are invalid")
        if not isinstance(self.status, CatalogWorkflowStatus):
            raise ValueError("workflow status is invalid")
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise ValueError("workflow version must be positive")
        if (
            isinstance(self.product_version, bool)
            or not isinstance(self.product_version, int)
            or self.product_version < 1
        ):
            raise ValueError("workflow Product version must be positive")
        if not 0 <= self.progress_percent <= 100:
            raise ValueError("workflow progress must be between 0 and 100")
        expected = tuple(CatalogWorkflowStageName)
        if tuple(stage.stage for stage in self.stages) != expected or len(self.stages) > 20:
            raise ValueError("workflow stages must use the fixed ordered pipeline")
        if not self.source_snapshot or len(self.source_snapshot) > 50:
            raise ValueError("workflow source snapshot must contain 1 through 50 sources")
        if len({item.source_id for item in self.source_snapshot}) != len(self.source_snapshot):
            raise ValueError("workflow source snapshot contains duplicates")
        if self.current_stage is not None and self.current_stage not in expected:
            raise ValueError("workflow current stage is invalid")
        created = _utc(self.created_at, "created_at")
        updated = _utc(self.updated_at, "updated_at")
        started = _utc(self.started_at, "started_at")
        completed = _utc(self.completed_at, "completed_at")
        assert created is not None and updated is not None
        if updated < created or (started is not None and started < created):
            raise ValueError("workflow timestamps are out of order")
        if completed is not None and completed < (started or created):
            raise ValueError("workflow completion precedes activity")
        if self.status in TERMINAL_WORKFLOW_STATUSES and completed is None:
            raise ValueError("terminal workflow requires completion time")
        if self.status not in TERMINAL_WORKFLOW_STATUSES and completed is not None:
            raise ValueError("non-terminal workflow cannot have completion time")
        if self.status is CatalogWorkflowStatus.WAITING_FOR_REVIEW and self.review_id is None:
            raise ValueError("review-waiting workflow requires review_id")
        if self.status is CatalogWorkflowStatus.FAILED and not self.error_code:
            raise ValueError("failed workflow requires error code")
        object.__setattr__(self, "created_at", created)
        object.__setattr__(self, "updated_at", updated)
        object.__setattr__(self, "started_at", started)
        object.__setattr__(self, "completed_at", completed)

    @property
    def next_action(self) -> CatalogWorkflowNextAction:
        if self.status is not CatalogWorkflowStatus.WAITING_FOR_REVIEW:
            return CatalogWorkflowNextAction.NONE
        review_stage = self.stages[
            tuple(CatalogWorkflowStageName).index(CatalogWorkflowStageName.HUMAN_REVIEW)
        ]
        return (
            CatalogWorkflowNextAction.COMPLETE_PRODUCT_REVIEW
            if review_stage.status is CatalogWorkflowStageStatus.WAITING
            else CatalogWorkflowNextAction.RESUME_WORKFLOW
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogWorkflowHistoryItem:
    workflow_id: UUID
    product_id: UUID
    status: CatalogWorkflowStatus
    progress_percent: int
    current_stage: CatalogWorkflowStageName | None
    created_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True, slots=True)
class CatalogWorkflowHistoryPage:
    items: tuple[CatalogWorkflowHistoryItem, ...]
    next_cursor: str | None
