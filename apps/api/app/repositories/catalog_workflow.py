"""Catalog Intelligence workflow persistence contract."""

from typing import Protocol
from uuid import UUID

from app.domain.catalog_workflow import (
    CatalogIntelligenceWorkflow,
    CatalogWorkflowHistoryPage,
)


class CatalogIntelligenceWorkflowRepository(Protocol):
    def create(self, workflow: CatalogIntelligenceWorkflow) -> CatalogIntelligenceWorkflow: ...

    def get_by_id(self, workflow_id: UUID) -> CatalogIntelligenceWorkflow | None: ...

    def save_state(
        self, workflow: CatalogIntelligenceWorkflow, *, expected_version: int
    ) -> CatalogIntelligenceWorkflow: ...

    def list_by_product(
        self, product_id: UUID, *, limit: int = 20, cursor: str | None = None
    ) -> CatalogWorkflowHistoryPage: ...
