"""Structured attribute extraction result repository contract."""

from typing import Protocol
from uuid import UUID

from app.domain.attribute_extraction import StructuredAttributeExtractionResult


class StructuredAttributeExtractionResultRepository(Protocol):
    def create(
        self, result: StructuredAttributeExtractionResult
    ) -> StructuredAttributeExtractionResult: ...
    def get_by_id(self, extraction_id: UUID) -> StructuredAttributeExtractionResult | None: ...
    def get_by_job_id(self, job_id: UUID) -> StructuredAttributeExtractionResult | None: ...
