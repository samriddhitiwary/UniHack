"""SPEC-037 public workflow API contract tests."""

# mypy: disable-error-code="no-untyped-def"

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies.catalog_workflows import get_catalog_workflow_service
from app.domain.catalog_workflow import (
    CatalogIntelligenceWorkflowConfiguration,
    CatalogWorkflowHistoryItem,
    CatalogWorkflowHistoryPage,
    CatalogWorkflowSourceSnapshot,
    CatalogWorkflowStageName,
    CatalogWorkflowStageOutcome,
    CatalogWorkflowStageStatus,
)
from app.domain.product_sources import ProductSourceType
from app.main import app
from app.services.catalog_workflow_state_machine import CatalogWorkflowStateMachine


def _waiting_workflow(product_id):
    state = CatalogWorkflowStateMachine(clock=lambda: datetime(2026, 8, 20, tzinfo=UTC))
    workflow = state.create(
        product_id=product_id,
        product_version=1,
        configuration=CatalogIntelligenceWorkflowConfiguration(),
        source_snapshot=(
            CatalogWorkflowSourceSnapshot(source_id=uuid4(), source_type=ProductSourceType.TEXT),
        ),
    )
    workflow = state.begin(workflow)
    for stage in tuple(CatalogWorkflowStageName)[:8]:
        workflow = state.start_stage(workflow, stage)
        workflow = state.apply_outcome(
            workflow,
            stage,
            CatalogWorkflowStageOutcome(status=CatalogWorkflowStageStatus.COMPLETED),
        )
    workflow = state.start_stage(workflow, CatalogWorkflowStageName.HUMAN_REVIEW)
    return state.apply_outcome(
        workflow,
        CatalogWorkflowStageName.HUMAN_REVIEW,
        CatalogWorkflowStageOutcome(
            status=CatalogWorkflowStageStatus.WAITING,
            review_id=uuid4(),
            result_reference="product-reviews/review",
        ),
    )


class WorkflowApiService:
    def __init__(self, workflow) -> None:
        self.workflow = workflow

    def start(self, *, product_id, configuration):
        assert configuration.generate_export is False
        return self.workflow

    def get(self, *, product_id, workflow_id):
        assert workflow_id == self.workflow.workflow_id
        return self.workflow

    def list(self, *, product_id, limit=20, cursor=None):
        item = CatalogWorkflowHistoryItem(
            workflow_id=self.workflow.workflow_id,
            product_id=product_id,
            status=self.workflow.status,
            progress_percent=self.workflow.progress_percent,
            current_stage=self.workflow.current_stage,
            created_at=self.workflow.created_at,
            completed_at=None,
        )
        return CatalogWorkflowHistoryPage((item,), None)

    def resume(self, *, product_id, workflow_id, expected_version):
        assert expected_version == self.workflow.version
        return self.workflow


def test_workflow_start_get_list_and_resume_contract(client: TestClient) -> None:
    product_id = uuid4()
    workflow = _waiting_workflow(product_id)
    app.dependency_overrides[get_catalog_workflow_service] = lambda: WorkflowApiService(workflow)

    started = client.post(
        f"/api/v1/products/{product_id}/workflows",
        json={"generateExport": False},
    )
    assert started.status_code == 201
    assert started.json()["status"] == "WAITING_FOR_REVIEW"
    assert started.json()["nextAction"] == "COMPLETE_PRODUCT_REVIEW"
    assert started.json()["reviewId"] == str(workflow.review_id)

    retrieved = client.get(f"/api/v1/products/{product_id}/workflows/{workflow.workflow_id}")
    assert retrieved.status_code == 200
    assert retrieved.json()["workflowId"] == str(workflow.workflow_id)

    history = client.get(f"/api/v1/products/{product_id}/workflows")
    assert history.status_code == 200
    assert history.json()["items"][0]["workflowId"] == str(workflow.workflow_id)

    resumed = client.post(
        f"/api/v1/products/{product_id}/workflows/{workflow.workflow_id}/resume",
        json={"version": workflow.version},
    )
    assert resumed.status_code == 200


def test_workflow_request_rejects_unknown_configuration_fields(client: TestClient) -> None:
    product_id = uuid4()
    workflow = _waiting_workflow(product_id)
    app.dependency_overrides[get_catalog_workflow_service] = lambda: WorkflowApiService(workflow)
    response = client.post(
        f"/api/v1/products/{product_id}/workflows",
        json={"stages": ["HUMAN_REVIEW"]},
    )
    assert response.status_code == 422
