"""Read-only Product Intelligence Score detail and history service."""

import logging
from uuid import UUID

from app.core.exceptions import (
    InvalidProductIntelligenceCursorError,
    ProductIntelligenceReadError,
    ProductIntelligenceScoreNotFoundError,
    ProductIntelligenceScoreRepositoryError,
    ProductNotFoundError,
    ProductRepositoryError,
)
from app.domain.product_intelligence import (
    ProductIntelligenceScorePage,
    ProductIntelligenceScoreResult,
)
from app.repositories.product_intelligence import ProductIntelligenceScoreRepository
from app.repositories.products import ProductRepository

logger = logging.getLogger(__name__)


class ProductIntelligenceReadService:
    def __init__(
        self,
        product_repository: ProductRepository,
        score_repository: ProductIntelligenceScoreRepository,
    ) -> None:
        self._products = product_repository
        self._scores = score_repository

    def get_score(self, product_id: UUID, score_id: UUID) -> ProductIntelligenceScoreResult:
        self._require_product(product_id)
        try:
            score = self._scores.get_by_id(score_id)
        except ProductIntelligenceScoreRepositoryError as exc:
            raise ProductIntelligenceReadError() from exc
        if score is None or score.product_id != product_id:
            raise ProductIntelligenceScoreNotFoundError(product_id, score_id)
        logger.info(
            "event=product_intelligence.read product_id=%s score_id=%s", product_id, score_id
        )
        return score

    def list_history(
        self, product_id: UUID, *, limit: int = 20, cursor: str | None = None
    ) -> ProductIntelligenceScorePage:
        self._require_product(product_id)
        try:
            page = self._scores.list_by_product(product_id, limit=limit, cursor=cursor)
        except InvalidProductIntelligenceCursorError:
            raise
        except ProductIntelligenceScoreRepositoryError as exc:
            raise ProductIntelligenceReadError() from exc
        logger.info(
            "event=product_intelligence.history_read product_id=%s limit=%s result_count=%s",
            product_id,
            limit,
            len(page.items),
        )
        return page

    def _require_product(self, product_id: UUID) -> None:
        try:
            if self._products.get_by_id(product_id) is None:
                raise ProductNotFoundError(product_id)
        except ProductNotFoundError:
            raise
        except ProductRepositoryError as exc:
            raise ProductIntelligenceReadError() from exc
