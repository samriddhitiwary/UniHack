"""Attribute selection result repository contract."""

from typing import Protocol
from uuid import UUID

from app.domain.attribute_selection import AttributeSelectionResult


class AttributeSelectionResultRepository(Protocol):
    def create(self, result: AttributeSelectionResult) -> AttributeSelectionResult: ...
    def get_by_id(self, selection_id: UUID) -> AttributeSelectionResult | None: ...
    def get_by_job_id(self, job_id: UUID) -> AttributeSelectionResult | None: ...
