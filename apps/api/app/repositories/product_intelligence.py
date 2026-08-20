"""Product Intelligence Score repository contract."""

from typing import Protocol
from uuid import UUID

from app.domain.product_intelligence import (
    ProductIntelligenceScorePage,
    ProductIntelligenceScoreResult,
)


class ProductIntelligenceScoreRepository(Protocol):
    def create(self, result: ProductIntelligenceScoreResult) -> ProductIntelligenceScoreResult: ...
    def get_by_id(self, score_id: UUID) -> ProductIntelligenceScoreResult | None: ...
    def get_by_job_id(self, job_id: UUID) -> ProductIntelligenceScoreResult | None: ...
    def get_by_input_key(self, input_key: str) -> ProductIntelligenceScoreResult | None: ...
    def get_by_projection_id(
        self, projection_id: UUID
    ) -> tuple[ProductIntelligenceScoreResult, ...]: ...
    def list_by_product(
        self, product_id: UUID, *, limit: int, cursor: str | None = None
    ) -> ProductIntelligenceScorePage: ...
