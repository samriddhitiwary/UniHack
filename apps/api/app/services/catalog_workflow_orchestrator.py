"""Synchronous fixed-pipeline orchestration for Catalog Intelligence workflows."""

import logging
from typing import Protocol
from uuid import UUID

from app.core.exceptions import (
    CatalogWorkflowNoProductSourcesError,
    CatalogWorkflowNotFoundError,
    CatalogWorkflowResumeNotAllowedError,
    CatalogWorkflowReviewNotCompletedError,
    CatalogWorkflowSourceLimitExceededError,
    CatalogWorkflowVersionConflictError,
    ProductNotFoundError,
)
from app.domain.catalog_workflow import (
    OPTIONAL_STAGES,
    CatalogIntelligenceWorkflow,
    CatalogIntelligenceWorkflowConfiguration,
    CatalogWorkflowHistoryPage,
    CatalogWorkflowSourceSnapshot,
    CatalogWorkflowStageName,
    CatalogWorkflowStageOutcome,
    CatalogWorkflowStageStatus,
    CatalogWorkflowStatus,
)
from app.domain.product_sources import ProductSource
from app.domain.products import Product
from app.repositories.catalog_workflow import CatalogIntelligenceWorkflowRepository
from app.repositories.product_sources import ProductSourceRepository
from app.repositories.products import ProductRepository
from app.services.catalog_workflow_state_machine import CatalogWorkflowStateMachine

logger = logging.getLogger(__name__)


class CatalogWorkflowStageExecutor(Protocol):
    """Adapter boundary implemented by the existing stage-service runtime."""

    def execute(
        self,
        stage: CatalogWorkflowStageName,
        workflow: CatalogIntelligenceWorkflow,
    ) -> CatalogWorkflowStageOutcome: ...

    def review_is_completed(self, workflow: CatalogIntelligenceWorkflow) -> bool: ...

    def completion_has_warnings(self, workflow: CatalogIntelligenceWorkflow) -> bool: ...


class CatalogIntelligenceWorkflowService:
    """Persist every transition and execute only the fixed next stage."""

    def __init__(
        self,
        *,
        workflow_repository: CatalogIntelligenceWorkflowRepository,
        product_repository: ProductRepository,
        source_repository: ProductSourceRepository,
        executor: CatalogWorkflowStageExecutor,
        state_machine: CatalogWorkflowStateMachine | None = None,
        max_sources: int = 50,
    ) -> None:
        self._workflows = workflow_repository
        self._products = product_repository
        self._sources = source_repository
        self._executor = executor
        self._state = state_machine or CatalogWorkflowStateMachine()
        self._max_sources = max_sources

    def start(
        self,
        *,
        product_id: UUID,
        configuration: CatalogIntelligenceWorkflowConfiguration,
    ) -> CatalogIntelligenceWorkflow:
        product = self._require_product(product_id)
        snapshot = self._source_snapshot(product_id)
        workflow = self._state.create(
            product_id=product_id,
            product_version=product.version,
            configuration=configuration,
            source_snapshot=snapshot,
        )
        self._workflows.create(workflow)
        workflow = self._save(self._state.begin(workflow), workflow.version)
        logger.info(
            "event=catalog_workflow.started workflow_id=%s product_id=%s source_count=%s",
            workflow.workflow_id,
            product_id,
            len(snapshot),
        )
        return self._run(workflow)

    def get(self, *, product_id: UUID, workflow_id: UUID) -> CatalogIntelligenceWorkflow:
        workflow = self._workflows.get_by_id(workflow_id)
        if workflow is None or workflow.product_id != product_id:
            raise CatalogWorkflowNotFoundError()
        return workflow

    def list(
        self, *, product_id: UUID, limit: int = 20, cursor: str | None = None
    ) -> CatalogWorkflowHistoryPage:
        self._require_product(product_id)
        return self._workflows.list_by_product(product_id, limit=limit, cursor=cursor)

    def resume(
        self, *, product_id: UUID, workflow_id: UUID, expected_version: int
    ) -> CatalogIntelligenceWorkflow:
        workflow = self.get(product_id=product_id, workflow_id=workflow_id)
        if workflow.version != expected_version:
            raise CatalogWorkflowVersionConflictError()
        if workflow.status is not CatalogWorkflowStatus.WAITING_FOR_REVIEW:
            raise CatalogWorkflowResumeNotAllowedError()
        if self._source_snapshot(product_id) != workflow.source_snapshot:
            raise CatalogWorkflowResumeNotAllowedError(
                "Product sources changed while the workflow was paused."
            )
        product = self._products.get_by_id(product_id)
        if product is None or product.version != workflow.product_version:
            raise CatalogWorkflowResumeNotAllowedError(
                "Product changed while the workflow was paused."
            )
        if not self._executor.review_is_completed(workflow):
            raise CatalogWorkflowReviewNotCompletedError()
        workflow = self._save(self._state.resume_review(workflow), workflow.version)
        logger.info(
            "event=catalog_workflow.resumed workflow_id=%s product_id=%s version=%s",
            workflow_id,
            product_id,
            workflow.version,
        )
        return self._run(workflow)

    def _run(self, workflow: CatalogIntelligenceWorkflow) -> CatalogIntelligenceWorkflow:
        while workflow.status is CatalogWorkflowStatus.RUNNING:
            stage_name = workflow.current_stage
            if stage_name is None:
                finished = self._state.finish(
                    workflow,
                    with_warnings=self._executor.completion_has_warnings(workflow)
                    or any(
                        stage.status is CatalogWorkflowStageStatus.FAILED
                        for stage in workflow.stages
                    ),
                )
                return self._save(finished, workflow.version)
            stage = next(item for item in workflow.stages if item.stage is stage_name)
            if stage.status is CatalogWorkflowStageStatus.NOT_STARTED:
                workflow = self._save(
                    self._state.start_stage(workflow, stage_name), workflow.version
                )
            elif stage.status is not CatalogWorkflowStageStatus.RUNNING:
                raise CatalogWorkflowResumeNotAllowedError()
            try:
                outcome = self._executor.execute(stage_name, workflow)
                workflow = self._save(
                    self._state.apply_outcome(workflow, stage_name, outcome),
                    workflow.version,
                )
            except Exception as exc:
                code = str(getattr(exc, "code", "WORKFLOW_STAGE_FAILED"))[:100]
                message = str(getattr(exc, "safe_message", "Workflow stage execution failed."))[
                    :2_000
                ]
                optional = stage_name in OPTIONAL_STAGES
                terminal = not optional or workflow.configuration.fail_on_optional_stage_error
                logger.warning(
                    "event=catalog_workflow.stage_failed workflow_id=%s product_id=%s "
                    "stage=%s code=%s terminal=%s",
                    workflow.workflow_id,
                    workflow.product_id,
                    stage_name.value,
                    code,
                    terminal,
                )
                workflow = self._save(
                    self._state.fail_stage(
                        workflow,
                        stage_name,
                        error_code=code,
                        error_message=message,
                        terminal=terminal,
                    ),
                    workflow.version,
                )
                if terminal:
                    return workflow
            if workflow.status is CatalogWorkflowStatus.WAITING_FOR_REVIEW:
                return workflow
        return workflow

    def _source_snapshot(self, product_id: UUID) -> tuple[CatalogWorkflowSourceSnapshot, ...]:
        sources: list[ProductSource] = []
        cursor: str | None = None
        while True:
            page = self._sources.list_by_product(
                product_id,
                limit=min(25, self._max_sources + 1 - len(sources)),
                cursor=cursor,
            )
            sources.extend(page.items)
            if len(sources) > self._max_sources:
                raise CatalogWorkflowSourceLimitExceededError()
            cursor = page.next_cursor
            if cursor is None:
                break
        if not sources:
            raise CatalogWorkflowNoProductSourcesError()
        return tuple(
            CatalogWorkflowSourceSnapshot(
                source_id=source.source_id,
                source_type=source.source_type,
            )
            for source in sorted(sources, key=lambda item: str(item.source_id))
        )

    def _require_product(self, product_id: UUID) -> Product:
        product = self._products.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        return product

    def _save(
        self, workflow: CatalogIntelligenceWorkflow, expected_version: int
    ) -> CatalogIntelligenceWorkflow:
        return self._workflows.save_state(workflow, expected_version=expected_version)
