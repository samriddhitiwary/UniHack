"""Product-classification result repository contract."""

from typing import Protocol
from uuid import UUID

from app.domain.product_classification import ProductClassificationResult


class ProductClassificationResultRepository(Protocol):
    def create(self, result: ProductClassificationResult) -> ProductClassificationResult: ...
    def get_by_id(self, classification_id: UUID) -> ProductClassificationResult | None: ...
    def get_by_job_id(self, job_id: UUID) -> ProductClassificationResult | None: ...
