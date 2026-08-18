"""Attribute validation result repository contract."""

from typing import Protocol
from uuid import UUID

from app.domain.attribute_validation import AttributeValidationResult


class AttributeValidationResultRepository(Protocol):
    def create(self, result: AttributeValidationResult) -> AttributeValidationResult: ...
    def get_by_id(self, validation_id: UUID) -> AttributeValidationResult | None: ...
    def get_by_job_id(self, job_id: UUID) -> AttributeValidationResult | None: ...
