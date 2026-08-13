"""Attribute normalization result repository contract."""

from typing import Protocol
from uuid import UUID

from app.domain.attribute_normalization import AttributeNormalizationResult


class AttributeNormalizationResultRepository(Protocol):
    def create(self, result: AttributeNormalizationResult) -> AttributeNormalizationResult: ...
    def get_by_id(self, normalization_id: UUID) -> AttributeNormalizationResult | None: ...
    def get_by_job_id(self, job_id: UUID) -> AttributeNormalizationResult | None: ...
