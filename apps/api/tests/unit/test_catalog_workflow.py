"""Workflow planning, state, pause/resume, failure, and idempotency tests."""

from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.exceptions import (
    CatalogWorkflowNoProductSourcesError,
    CatalogWorkflowReviewNotCompletedError,
    CatalogWorkflowVersionConflictError,
)
from app.domain.catalog_workflow import (
    CatalogIntelligenceWorkflowConfiguration,
    CatalogWorkflowHistoryPage,
    CatalogWorkflowSourceSnapshot,
    CatalogWorkflowStageName,
    CatalogWorkflowStageOutcome,
    CatalogWorkflowStageStatus,
    CatalogWorkflowStatus,
)
from app.domain.processing_jobs import ProcessingJobType
from app.domain.product_sources import ProductSourceType
from app.services.catalog_workflow_orchestrator import CatalogIntelligenceWorkflowService
from app.services.catalog_workflow_planner import CatalogWorkflowPlanner


class MemoryWorkflowRepository:
    def __init__(self) -> None:
        self.value = None

    def create(self, workflow):
        if self.value is not None and self.value.status not in {
            CatalogWorkflowStatus.COMPLETED,
            CatalogWorkflowStatus.COMPLETED_WITH_WARNINGS,
            CatalogWorkflowStatus.FAILED,
        }:
            raise RuntimeError("active")
        self.value = workflow
        return workflow

    def get_by_id(self, workflow_id):
        return self.value if self.value and self.value.workflow_id == workflow_id else None

    def save_state(self, workflow, *, expected_version):
        assert self.value.version == expected_version
        assert workflow.version == expected_version + 1
        self.value = workflow
        return workflow

    def list_by_product(self, product_id, *, limit=20, cursor=None):
        return CatalogWorkflowHistoryPage(items=(), next_cursor=None)


class FakeExecutor:
    def __init__(self) -> None:
        self.review_completed = False
        self.fail_stage = None
        self.warning = False
        self.executions: list[CatalogWorkflowStageName] = []
        self.inputs = []
        self.ids = {stage: uuid4() for stage in CatalogWorkflowStageName}

    def execute(self, stage, workflow):
        self.executions.append(stage)
        self.inputs.append(workflow)
        if stage is self.fail_stage:
            raise RuntimeError("controlled test failure")
        if stage is CatalogWorkflowStageName.HUMAN_REVIEW and not self.review_completed:
            return CatalogWorkflowStageOutcome(
                status=CatalogWorkflowStageStatus.WAITING,
                review_id=self.ids[stage],
                result_reference=f"product-reviews/{self.ids[stage]}",
            )
        field = {
            CatalogWorkflowStageName.PRODUCT_CLASSIFICATION: "classification_id",
            CatalogWorkflowStageName.ATTRIBUTE_EXTRACTION: "extraction_id",
            CatalogWorkflowStageName.ATTRIBUTE_NORMALIZATION: "normalization_id",
            CatalogWorkflowStageName.CONFLICT_DETECTION: "conflict_detection_id",
            CatalogWorkflowStageName.COMPLETENESS: "completeness_id",
            CatalogWorkflowStageName.ATTRIBUTE_VALIDATION: "validation_id",
            CatalogWorkflowStageName.ATTRIBUTE_SELECTION: "selection_id",
            CatalogWorkflowStageName.HUMAN_REVIEW: "review_id",
            CatalogWorkflowStageName.REVIEWED_ATTRIBUTE_MATERIALIZATION: "materialization_id",
            CatalogWorkflowStageName.CATALOG_PROJECTION: "projection_id",
            CatalogWorkflowStageName.CATALOG_EXPORT: "export_id",
            CatalogWorkflowStageName.AI_ENRICHMENT: "enrichment_id",
            CatalogWorkflowStageName.PRODUCT_INTELLIGENCE_SCORE: "score_id",
        }.get(stage)
        kwargs = {field: self.ids[stage]} if field else {}
        return CatalogWorkflowStageOutcome(
            status=CatalogWorkflowStageStatus.COMPLETED,
            result_reference=f"results/{self.ids[stage]}",
            **kwargs,
        )

    def review_is_completed(self, workflow):
        return (
            self.review_completed
            and workflow.review_id == self.ids[CatalogWorkflowStageName.HUMAN_REVIEW]
        )

    def completion_has_warnings(self, workflow):
        return self.warning


def _service(source_types=(ProductSourceType.TEXT,)):
    workflow_repository = MemoryWorkflowRepository()
    product_id = uuid4()
    product = SimpleNamespace(product_id=product_id, version=1)
    products = SimpleNamespace(get_by_id=lambda value: product if value == product_id else None)
    sources = tuple(
        SimpleNamespace(source_id=uuid4(), source_type=source_type) for source_type in source_types
    )
    source_repo = SimpleNamespace(
        list_by_product=lambda product_id, limit=25, cursor=None: SimpleNamespace(
            items=sources, next_cursor=None
        )
    )
    executor = FakeExecutor()
    return (
        CatalogIntelligenceWorkflowService(
            workflow_repository=workflow_repository,
            product_repository=products,
            source_repository=source_repo,
            executor=executor,
        ),
        product_id,
        executor,
    )


@pytest.mark.parametrize(
    ("source_type", "expected"),
    [
        (ProductSourceType.TEXT, ()),
        (
            ProductSourceType.PDF,
            (ProcessingJobType.PDF_TEXT_EXTRACTION, ProcessingJobType.PDF_TABLE_EXTRACTION),
        ),
        (ProductSourceType.CSV, (ProcessingJobType.CSV_PROCESSING,)),
        (
            ProductSourceType.IMAGE,
            (ProcessingJobType.IMAGE_ANALYSIS, ProcessingJobType.IMAGE_OCR),
        ),
    ],
)
def test_source_planner_maps_exact_jobs(source_type, expected) -> None:
    source = CatalogWorkflowSourceSnapshot(source_id=uuid4(), source_type=source_type)
    assert CatalogWorkflowPlanner().plan_sources((source,))[0].job_types == expected


def test_source_planner_enforces_child_job_limit() -> None:
    sources = tuple(
        CatalogWorkflowSourceSnapshot(source_id=uuid4(), source_type=ProductSourceType.IMAGE)
        for _ in range(101)
    )
    with pytest.raises(ValueError, match="child-job limit"):
        CatalogWorkflowPlanner().plan_sources(sources)


def test_workflow_pauses_for_review_then_resumes_without_rerunning_completed_stages() -> None:
    service, product_id, executor = _service(
        (ProductSourceType.TEXT, ProductSourceType.PDF, ProductSourceType.IMAGE)
    )
    waiting = service.start(
        product_id=product_id,
        configuration=CatalogIntelligenceWorkflowConfiguration(),
    )
    assert waiting.status is CatalogWorkflowStatus.WAITING_FOR_REVIEW
    assert waiting.current_stage is CatalogWorkflowStageName.HUMAN_REVIEW
    assert waiting.review_id is not None
    assert waiting.progress_percent == 53
    before = tuple(executor.executions)
    with pytest.raises(CatalogWorkflowReviewNotCompletedError):
        service.resume(
            product_id=product_id,
            workflow_id=waiting.workflow_id,
            expected_version=waiting.version,
        )
    executor.review_completed = True
    completed = service.resume(
        product_id=product_id,
        workflow_id=waiting.workflow_id,
        expected_version=waiting.version,
    )
    assert completed.status is CatalogWorkflowStatus.COMPLETED
    assert completed.progress_percent == 100
    assert executor.executions[: len(before)] == list(before)
    assert executor.executions.count(CatalogWorkflowStageName.PRODUCT_CLASSIFICATION) == 1
    assert executor.executions.count(CatalogWorkflowStageName.HUMAN_REVIEW) == 2


def test_resume_rejects_stale_workflow_version() -> None:
    service, product_id, _ = _service()
    waiting = service.start(
        product_id=product_id,
        configuration=CatalogIntelligenceWorkflowConfiguration(),
    )
    with pytest.raises(CatalogWorkflowVersionConflictError):
        service.resume(
            product_id=product_id,
            workflow_id=waiting.workflow_id,
            expected_version=waiting.version - 1,
        )


def test_core_stage_failure_is_terminal() -> None:
    service, product_id, executor = _service()
    executor.fail_stage = CatalogWorkflowStageName.PRODUCT_CLASSIFICATION
    failed = service.start(
        product_id=product_id,
        configuration=CatalogIntelligenceWorkflowConfiguration(),
    )
    assert failed.status is CatalogWorkflowStatus.FAILED
    assert failed.error_code == "WORKFLOW_STAGE_FAILED"
    assert CatalogWorkflowStageName.ATTRIBUTE_EXTRACTION not in executor.executions


def test_start_rejects_product_without_sources() -> None:
    service, product_id, _ = _service(())
    with pytest.raises(CatalogWorkflowNoProductSourcesError):
        service.start(
            product_id=product_id,
            configuration=CatalogIntelligenceWorkflowConfiguration(),
        )


def test_optional_failure_continues_to_score_without_enrichment() -> None:
    service, product_id, executor = _service()
    executor.review_completed = True
    executor.fail_stage = CatalogWorkflowStageName.AI_ENRICHMENT
    completed = service.start(
        product_id=product_id,
        configuration=CatalogIntelligenceWorkflowConfiguration(fail_on_optional_stage_error=False),
    )
    assert completed.status is CatalogWorkflowStatus.COMPLETED_WITH_WARNINGS
    score_index = executor.executions.index(CatalogWorkflowStageName.PRODUCT_INTELLIGENCE_SCORE)
    assert executor.inputs[score_index].enrichment_id is None


def test_strict_optional_failure_fails_workflow() -> None:
    service, product_id, executor = _service()
    executor.review_completed = True
    executor.fail_stage = CatalogWorkflowStageName.CATALOG_EXPORT
    failed = service.start(
        product_id=product_id,
        configuration=CatalogIntelligenceWorkflowConfiguration(fail_on_optional_stage_error=True),
    )
    assert failed.status is CatalogWorkflowStatus.FAILED
    assert CatalogWorkflowStageName.AI_ENRICHMENT not in executor.executions


def test_ready_with_warnings_projection_completes_with_warnings() -> None:
    service, product_id, executor = _service()
    executor.review_completed = True
    executor.warning = True
    completed = service.start(
        product_id=product_id,
        configuration=CatalogIntelligenceWorkflowConfiguration(),
    )
    assert completed.status is CatalogWorkflowStatus.COMPLETED_WITH_WARNINGS


def test_configuration_is_immutable_and_stage_order_is_fixed() -> None:
    config = CatalogIntelligenceWorkflowConfiguration(generate_export=False)
    with pytest.raises(FrozenInstanceError):
        config.generate_export = True  # type: ignore[misc]
    assert next(iter(CatalogWorkflowStageName)) is CatalogWorkflowStageName.SOURCE_PROCESSING
    assert (
        tuple(CatalogWorkflowStageName)[-1] is CatalogWorkflowStageName.PRODUCT_INTELLIGENCE_SCORE
    )
