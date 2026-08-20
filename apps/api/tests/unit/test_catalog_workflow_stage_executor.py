"""Existing-service adapter lineage, source, review, and optional-stage tests."""

# mypy: disable-error-code="no-untyped-def"

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.api.dependencies.catalog_workflows import (
    get_catalog_workflow_repository,
    get_catalog_workflow_service,
    get_catalog_workflow_stage_executor,
)
from app.core.config import Settings
from app.domain.catalog_projection import CatalogProjectionStatus
from app.domain.catalog_workflow import (
    CatalogIntelligenceWorkflowConfiguration,
    CatalogWorkflowSkipReason,
    CatalogWorkflowSourceSnapshot,
    CatalogWorkflowStageName,
    CatalogWorkflowStageStatus,
)
from app.domain.processing_jobs import ProcessingJobStatus, ProcessingJobType
from app.domain.product_review import ProductReviewSessionStatus
from app.domain.product_sources import ProductSourceType
from app.domain.products import Product, ProductStatus
from app.services.catalog_workflow_runtime import build_catalog_workflow_stage_executor
from app.services.catalog_workflow_stage_executor import (
    ExistingServicesCatalogWorkflowStageExecutor,
)
from app.services.catalog_workflow_state_machine import CatalogWorkflowStateMachine


class Jobs:
    def __init__(self) -> None:
        self.items = []

    def create(self, job):
        self.items.append(job)
        return job

    def list_by_source(self, product_id, source_id, *, limit=100, cursor=None):
        return SimpleNamespace(items=(), next_cursor=None)

    def list_by_product(self, product_id, *, limit=100, cursor=None):
        return SimpleNamespace(items=(), next_cursor=None)


class Products:
    def __init__(self) -> None:
        self.product = Product.create(name="Workflow Product")

    def get_by_id(self, product_id):
        return self.product if product_id == self.product.product_id else None

    def update(self, product, expected_version):
        self.product = replace(product, version=expected_version + 1)
        return self.product


def _runtime(*, config=None, projection_status=CatalogProjectionStatus.READY):
    jobs = Jobs()
    products = Products()
    review = SimpleNamespace(
        review_id=uuid4(),
        product_id=products.product.product_id,
        selection_id=uuid4(),
        status=ProductReviewSessionStatus.OPEN,
    )
    reviews = SimpleNamespace(
        get_by_id=lambda review_id: review if review_id == review.review_id else None,
        get_by_selection_id=lambda selection_id: (
            review if selection_id == review.selection_id else None
        ),
    )
    projection = SimpleNamespace(projection_id=uuid4(), status=projection_status)
    projections = SimpleNamespace(
        get_by_id=lambda projection_id: (
            projection if projection_id == projection.projection_id else None
        )
    )
    calls = []

    def runner(*, job_id):
        calls.append(job_id)
        return SimpleNamespace()

    runners = {
        job_type: runner
        for job_type in ProcessingJobType
        if job_type is not ProcessingJobType.SOURCE_PROCESSING
    }
    loaders = {job_type: lambda job_id: None for job_type in runners}
    executor = ExistingServicesCatalogWorkflowStageExecutor(
        job_repository=jobs,
        product_repository=products,
        review_repository=reviews,
        projection_repository=projections,
        review_service=SimpleNamespace(create_review=lambda **kwargs: review),
        readiness_service=SimpleNamespace(apply=lambda **kwargs: calls.append("readiness")),
        runners=runners,
        result_loaders=loaders,
    )
    workflow = CatalogWorkflowStateMachine().create(
        product_id=products.product.product_id,
        product_version=products.product.version,
        configuration=config or CatalogIntelligenceWorkflowConfiguration(),
        source_snapshot=(
            CatalogWorkflowSourceSnapshot(source_id=uuid4(), source_type=ProductSourceType.TEXT),
        ),
    )
    return executor, workflow, jobs, products, review, projection, calls


def test_mixed_source_processing_creates_only_required_child_jobs() -> None:
    executor, workflow, jobs, _, _, _, calls = _runtime()
    workflow = replace(
        workflow,
        source_snapshot=tuple(
            CatalogWorkflowSourceSnapshot(source_id=uuid4(), source_type=source_type)
            for source_type in ProductSourceType
        ),
    )
    outcome = executor.execute(CatalogWorkflowStageName.SOURCE_PROCESSING, workflow)
    assert outcome.status is CatalogWorkflowStageStatus.COMPLETED
    assert [job.job_type for job in jobs.items] == [
        ProcessingJobType.PDF_TEXT_EXTRACTION,
        ProcessingJobType.PDF_TABLE_EXTRACTION,
        ProcessingJobType.IMAGE_ANALYSIS,
        ProcessingJobType.IMAGE_OCR,
        ProcessingJobType.CSV_PROCESSING,
    ]
    assert len(calls) == 5
    assert all(job.status is ProcessingJobStatus.PENDING for job in jobs.items)


def test_human_review_is_never_auto_approved_and_sets_review_required() -> None:
    executor, workflow, _, products, review, _, _ = _runtime()
    workflow = replace(workflow, selection_id=review.selection_id)
    outcome = executor.execute(CatalogWorkflowStageName.HUMAN_REVIEW, workflow)
    assert outcome.status is CatalogWorkflowStageStatus.WAITING
    assert outcome.review_id == review.review_id
    assert products.product.status is ProductStatus.REVIEW_REQUIRED
    assert outcome.product_version == products.product.version


def test_disabled_and_blocked_optional_stages_are_skipped() -> None:
    executor, workflow, _, _, _, projection, _ = _runtime(
        config=CatalogIntelligenceWorkflowConfiguration(generate_export=False)
    )
    workflow = replace(workflow, projection_id=projection.projection_id)
    disabled = executor.execute(CatalogWorkflowStageName.CATALOG_EXPORT, workflow)
    assert disabled.status is CatalogWorkflowStageStatus.SKIPPED
    assert disabled.skip_reason == CatalogWorkflowSkipReason.DISABLED

    blocked_executor, blocked, _, _, _, blocked_projection, _ = _runtime(
        projection_status=CatalogProjectionStatus.BLOCKED
    )
    blocked = replace(blocked, projection_id=blocked_projection.projection_id)
    readiness = blocked_executor.execute(CatalogWorkflowStageName.PUBLISHING_READINESS, blocked)
    export = blocked_executor.execute(CatalogWorkflowStageName.CATALOG_EXPORT, blocked)
    assert readiness.skip_reason == CatalogWorkflowSkipReason.PROJECTION_BLOCKED
    assert export.skip_reason == CatalogWorkflowSkipReason.PROJECTION_BLOCKED


def test_default_runtime_composes_existing_services_without_initializing_ocr_or_ai() -> None:
    executor = build_catalog_workflow_stage_executor(
        client=MagicMock(),
        settings=Settings(app_env="test"),
        jobs=MagicMock(),
        products=MagicMock(),
        sources=MagicMock(),
        reviews=MagicMock(),
        projections=MagicMock(),
        review_service=MagicMock(),
        storage=MagicMock(),
    )
    assert isinstance(executor, ExistingServicesCatalogWorkflowStageExecutor)


def test_fastapi_dependency_providers_compose_workflow_runtime() -> None:
    settings = Settings(app_env="test")
    client = MagicMock()
    workflows = get_catalog_workflow_repository(client, settings)
    executor = get_catalog_workflow_stage_executor(
        client,
        settings,
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    service = get_catalog_workflow_service(workflows, MagicMock(), MagicMock(), executor)
    assert service is not None
