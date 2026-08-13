"""Attribute completeness result repository contract."""

from typing import Protocol
from uuid import UUID

from app.domain.attribute_completeness import AttributeCompletenessResult


class AttributeCompletenessResultRepository(Protocol):
    def create(self, result: AttributeCompletenessResult) -> AttributeCompletenessResult: ...
    def get_by_id(self, completeness_id: UUID) -> AttributeCompletenessResult | None: ...
    def get_by_job_id(self, job_id: UUID) -> AttributeCompletenessResult | None: ...
