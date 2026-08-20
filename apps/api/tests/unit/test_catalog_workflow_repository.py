"""Composite workflow persistence and scoped history cursor tests."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.core.exceptions import InvalidCatalogWorkflowCursorError
from app.domain.catalog_workflow import (
    CatalogIntelligenceWorkflowConfiguration,
    CatalogWorkflowSourceSnapshot,
)
from app.domain.product_sources import ProductSourceType
from app.repositories.dynamodb_catalog_workflow import (
    DynamoDBCatalogIntelligenceWorkflowRepository,
)
from app.services.catalog_workflow_state_machine import CatalogWorkflowStateMachine
from app.utils.dynamodb import deserialize_item, serialize_item


def _workflow():
    return CatalogWorkflowStateMachine(
        clock=lambda: datetime(2026, 8, 20, tzinfo=UTC), id_factory=uuid4
    ).create(
        product_id=uuid4(),
        product_version=1,
        configuration=CatalogIntelligenceWorkflowConfiguration(),
        source_snapshot=(
            CatalogWorkflowSourceSnapshot(source_id=uuid4(), source_type=ProductSourceType.TEXT),
        ),
    )


def test_meta_and_stage_records_round_trip_without_upstream_payloads() -> None:
    workflow = _workflow()
    repository = DynamoDBCatalogIntelligenceWorkflowRepository(object(), "workflows")
    records = [
        repository._meta(workflow),
        *(repository._stage(workflow.workflow_id, stage) for stage in workflow.stages),
    ]
    round_tripped = [deserialize_item(serialize_item(item)) for item in records]
    restored = repository._from_items(round_tripped)
    assert restored == workflow
    assert len(records) == 16
    assert all("attributes" not in record and "sourceContent" not in record for record in records)


def test_history_cursor_is_product_scoped_and_rejects_tampering() -> None:
    workflow = _workflow()
    key = serialize_item(
        {
            "workflowId": workflow.workflow_id,
            "recordKey": "META",
            "productId": workflow.product_id,
            "createdAt": workflow.created_at,
        }
    )
    cursor = DynamoDBCatalogIntelligenceWorkflowRepository._encode_cursor(key, workflow.product_id)
    assert cursor is not None
    assert (
        DynamoDBCatalogIntelligenceWorkflowRepository._decode_cursor(cursor, workflow.product_id)
        == key
    )
    with pytest.raises(InvalidCatalogWorkflowCursorError):
        DynamoDBCatalogIntelligenceWorkflowRepository._decode_cursor(cursor, uuid4())


class WorkflowClient:
    def __init__(self) -> None:
        self.transactions = []
        self.query_response = {"Items": []}
        self.query_requests = []

    def transact_write_items(self, **request):
        self.transactions.append(request)
        return {}

    def query(self, **request):
        self.query_requests.append(request)
        return self.query_response


def test_repository_create_read_save_and_indexed_history() -> None:
    client = WorkflowClient()
    repository = DynamoDBCatalogIntelligenceWorkflowRepository(client, "workflows")
    workflow = _workflow()

    assert repository.create(workflow) == workflow
    create_items = client.transactions[0]["TransactItems"]
    assert len(create_items) == 17
    assert create_items[0]["Put"]["Item"]["workflowId"]["S"].startswith("ACTIVE_PRODUCT#")

    records = [
        repository._meta(workflow),
        *(repository._stage(workflow.workflow_id, stage) for stage in workflow.stages),
    ]
    client.query_response = {"Items": [serialize_item(item) for item in records]}
    assert repository.get_by_id(workflow.workflow_id) == workflow
    assert client.query_requests[-1]["ConsistentRead"] is True

    running = CatalogWorkflowStateMachine(
        clock=lambda: datetime(2026, 8, 20, 0, 1, tzinfo=UTC)
    ).begin(workflow)
    assert repository.save_state(running, expected_version=workflow.version) == running
    assert len(client.transactions[-1]["TransactItems"]) == 16

    client.query_response = {"Items": [serialize_item(repository._meta(running))]}
    history = repository.list_by_product(workflow.product_id, limit=10)
    assert history.items[0].workflow_id == workflow.workflow_id
    assert history.next_cursor is None
    request = client.query_requests[-1]
    assert request["IndexName"] == "ProductCreatedAtIndex"
    assert request["ScanIndexForward"] is False
