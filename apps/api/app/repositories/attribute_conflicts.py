"""Attribute conflict detection result repository contract."""

from typing import Protocol
from uuid import UUID

from app.domain.attribute_conflicts import AttributeConflictDetectionResult


class AttributeConflictDetectionResultRepository(Protocol):
    def create(
        self, result: AttributeConflictDetectionResult
    ) -> AttributeConflictDetectionResult: ...
    def get_by_id(self, conflict_detection_id: UUID) -> AttributeConflictDetectionResult | None: ...
    def get_by_job_id(self, job_id: UUID) -> AttributeConflictDetectionResult | None: ...
