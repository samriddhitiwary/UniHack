"""Pure Catalog Intelligence workflow transitions and deterministic progress."""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from app.domain.catalog_workflow import (
    OPTIONAL_STAGES,
    TERMINAL_STAGE_STATUSES,
    TERMINAL_WORKFLOW_STATUSES,
    CatalogIntelligenceWorkflow,
    CatalogIntelligenceWorkflowConfiguration,
    CatalogIntelligenceWorkflowStage,
    CatalogWorkflowSourceSnapshot,
    CatalogWorkflowStageName,
    CatalogWorkflowStageOutcome,
    CatalogWorkflowStageStatus,
    CatalogWorkflowStatus,
)


class CatalogWorkflowStateMachine:
    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or uuid4

    def create(
        self,
        *,
        product_id: UUID,
        product_version: int,
        configuration: CatalogIntelligenceWorkflowConfiguration,
        source_snapshot: tuple[CatalogWorkflowSourceSnapshot, ...],
    ) -> CatalogIntelligenceWorkflow:
        now = self._clock()
        stages = tuple(
            CatalogIntelligenceWorkflowStage(stage=stage) for stage in CatalogWorkflowStageName
        )
        return CatalogIntelligenceWorkflow(
            workflow_id=self._id_factory(),
            product_id=product_id,
            product_version=product_version,
            status=CatalogWorkflowStatus.PENDING,
            version=1,
            configuration=configuration,
            source_snapshot=source_snapshot,
            current_stage=CatalogWorkflowStageName.SOURCE_PROCESSING,
            progress_percent=0,
            stages=stages,
            created_at=now,
            updated_at=now,
        )

    def begin(self, workflow: CatalogIntelligenceWorkflow) -> CatalogIntelligenceWorkflow:
        self._require_status(workflow, CatalogWorkflowStatus.PENDING)
        now = self._clock()
        return replace(
            workflow,
            status=CatalogWorkflowStatus.RUNNING,
            version=workflow.version + 1,
            started_at=now,
            updated_at=now,
        )

    def start_stage(
        self, workflow: CatalogIntelligenceWorkflow, stage_name: CatalogWorkflowStageName
    ) -> CatalogIntelligenceWorkflow:
        self._require_status(workflow, CatalogWorkflowStatus.RUNNING)
        stage = self._stage(workflow, stage_name)
        if stage.status is not CatalogWorkflowStageStatus.NOT_STARTED:
            raise ValueError("workflow stage cannot be started")
        now = self._clock()
        updated_stage = replace(
            stage,
            status=CatalogWorkflowStageStatus.RUNNING,
            started_at=now,
        )
        return self._replace_stage(
            workflow,
            updated_stage,
            status=CatalogWorkflowStatus.RUNNING,
            current_stage=stage_name,
            updated_at=now,
        )

    def apply_outcome(
        self,
        workflow: CatalogIntelligenceWorkflow,
        stage_name: CatalogWorkflowStageName,
        outcome: CatalogWorkflowStageOutcome,
    ) -> CatalogIntelligenceWorkflow:
        self._require_status(workflow, CatalogWorkflowStatus.RUNNING)
        stage = self._stage(workflow, stage_name)
        if stage.status is not CatalogWorkflowStageStatus.RUNNING:
            raise ValueError("workflow stage is not running")
        now = self._clock()
        completed_at = None if outcome.status is CatalogWorkflowStageStatus.WAITING else now
        updated_stage = replace(
            stage,
            status=outcome.status,
            job_id=outcome.job_id,
            child_job_ids=outcome.child_job_ids,
            result_reference=outcome.result_reference,
            completed_at=completed_at,
            skip_reason=outcome.skip_reason,
        )
        waiting = outcome.status is CatalogWorkflowStageStatus.WAITING
        changes = self._reference_changes(outcome)
        return self._replace_stage(
            workflow,
            updated_stage,
            status=(
                CatalogWorkflowStatus.WAITING_FOR_REVIEW
                if waiting
                else CatalogWorkflowStatus.RUNNING
            ),
            current_stage=(stage_name if waiting else self._next_stage(workflow, stage_name)),
            updated_at=now,
            **cast(Any, changes),
        )

    def resume_review(self, workflow: CatalogIntelligenceWorkflow) -> CatalogIntelligenceWorkflow:
        self._require_status(workflow, CatalogWorkflowStatus.WAITING_FOR_REVIEW)
        stage = self._stage(workflow, CatalogWorkflowStageName.HUMAN_REVIEW)
        if stage.status is not CatalogWorkflowStageStatus.WAITING:
            raise ValueError("workflow review stage is not waiting")
        now = self._clock()
        return self._replace_stage(
            workflow,
            replace(stage, status=CatalogWorkflowStageStatus.RUNNING),
            status=CatalogWorkflowStatus.RUNNING,
            current_stage=CatalogWorkflowStageName.HUMAN_REVIEW,
            updated_at=now,
        )

    def fail_stage(
        self,
        workflow: CatalogIntelligenceWorkflow,
        stage_name: CatalogWorkflowStageName,
        *,
        error_code: str,
        error_message: str,
        terminal: bool,
    ) -> CatalogIntelligenceWorkflow:
        stage = self._stage(workflow, stage_name)
        if stage.status is not CatalogWorkflowStageStatus.RUNNING:
            raise ValueError("workflow stage is not running")
        now = self._clock()
        failed = replace(
            stage,
            status=CatalogWorkflowStageStatus.FAILED,
            completed_at=now,
            error_code=error_code,
            error_message=error_message,
        )
        return self._replace_stage(
            workflow,
            failed,
            status=(CatalogWorkflowStatus.FAILED if terminal else CatalogWorkflowStatus.RUNNING),
            current_stage=(None if terminal else self._next_stage(workflow, stage_name)),
            updated_at=now,
            completed_at=(now if terminal else None),
            error_code=(error_code if terminal else None),
            error_message=(error_message if terminal else None),
        )

    def finish(
        self, workflow: CatalogIntelligenceWorkflow, *, with_warnings: bool
    ) -> CatalogIntelligenceWorkflow:
        self._require_status(workflow, CatalogWorkflowStatus.RUNNING)
        if any(stage.status not in TERMINAL_STAGE_STATUSES for stage in workflow.stages):
            raise ValueError("workflow has unfinished stages")
        if any(
            stage.status is CatalogWorkflowStageStatus.FAILED and stage.stage not in OPTIONAL_STAGES
            for stage in workflow.stages
        ):
            raise ValueError("workflow has a failed core stage")
        now = self._clock()
        return replace(
            workflow,
            status=(
                CatalogWorkflowStatus.COMPLETED_WITH_WARNINGS
                if with_warnings
                else CatalogWorkflowStatus.COMPLETED
            ),
            version=workflow.version + 1,
            current_stage=None,
            progress_percent=100,
            updated_at=now,
            completed_at=now,
        )

    @staticmethod
    def _stage(
        workflow: CatalogIntelligenceWorkflow, stage_name: CatalogWorkflowStageName
    ) -> CatalogIntelligenceWorkflowStage:
        return workflow.stages[tuple(CatalogWorkflowStageName).index(stage_name)]

    def _replace_stage(
        self,
        workflow: CatalogIntelligenceWorkflow,
        stage: CatalogIntelligenceWorkflowStage,
        **changes: object,
    ) -> CatalogIntelligenceWorkflow:
        stages = tuple(stage if item.stage is stage.stage else item for item in workflow.stages)
        progress = self.progress(stages)
        return replace(
            workflow,
            stages=stages,
            progress_percent=progress,
            version=workflow.version + 1,
            **cast(Any, changes),
        )

    @staticmethod
    def progress(stages: tuple[CatalogIntelligenceWorkflowStage, ...]) -> int:
        terminal_successes = sum(
            stage.status
            in {CatalogWorkflowStageStatus.COMPLETED, CatalogWorkflowStageStatus.SKIPPED}
            for stage in stages
        )
        return terminal_successes * 100 // len(stages)

    @staticmethod
    def _next_stage(
        workflow: CatalogIntelligenceWorkflow, current: CatalogWorkflowStageName
    ) -> CatalogWorkflowStageName | None:
        found = False
        for stage in workflow.stages:
            if stage.stage is current:
                found = True
                continue
            if found and stage.status is CatalogWorkflowStageStatus.NOT_STARTED:
                return stage.stage
        return None

    @staticmethod
    def _reference_changes(outcome: CatalogWorkflowStageOutcome) -> dict[str, object]:
        names = (
            "product_version",
            "classification_id",
            "extraction_id",
            "normalization_id",
            "conflict_detection_id",
            "completeness_id",
            "validation_id",
            "selection_id",
            "review_id",
            "materialization_id",
            "projection_id",
            "export_id",
            "enrichment_id",
            "score_id",
        )
        return {name: value for name in names if (value := getattr(outcome, name)) is not None}

    @staticmethod
    def _require_status(
        workflow: CatalogIntelligenceWorkflow, expected: CatalogWorkflowStatus
    ) -> None:
        if workflow.status in TERMINAL_WORKFLOW_STATUSES or workflow.status is not expected:
            raise ValueError("workflow status transition is invalid")
