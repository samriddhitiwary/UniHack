"""Bounded latest-artifact aggregation for catalog dashboard reads."""

import logging
from uuid import UUID

from app.core.exceptions import (
    CatalogEnrichmentRepositoryError,
    CatalogExportRepositoryError,
    CatalogProjectionRepositoryError,
    CatalogSearchStorageUnavailableError,
    ProductIntelligenceScoreRepositoryError,
    ProductNotFoundError,
    ProductRepositoryError,
)
from app.domain.catalog_search import (
    CatalogIntelligenceSummary,
    CatalogProductSummary,
    CatalogProjectionSummary,
)
from app.domain.products import Product
from app.repositories.catalog_enrichment import CatalogEnrichmentResultRepository
from app.repositories.catalog_export import CatalogExportResultRepository
from app.repositories.catalog_projection import CommerceCatalogProjectionRepository
from app.repositories.product_intelligence import ProductIntelligenceScoreRepository
from app.repositories.products import ProductRepository
from app.services.publishing_readiness_state import evaluate_publishing_readiness_state

logger = logging.getLogger(__name__)


class CatalogSummaryService:
    def __init__(
        self,
        *,
        product_repository: ProductRepository,
        projection_repository: CommerceCatalogProjectionRepository,
        score_repository: ProductIntelligenceScoreRepository,
        enrichment_repository: CatalogEnrichmentResultRepository,
        export_repository: CatalogExportResultRepository,
    ) -> None:
        self._products = product_repository
        self._projections = projection_repository
        self._scores = score_repository
        self._enrichments = enrichment_repository
        self._exports = export_repository

    def get_for_product(self, product_id: UUID) -> CatalogProductSummary:
        try:
            product = self._products.get_by_id(product_id)
            if product is None:
                raise ProductNotFoundError(product_id)
            result = self.summarize(product)
            logger.info(
                "event=catalog_summary.read product_id=%s projection_id=%s score_id=%s",
                product_id,
                result.latest_projection.projection_id if result.latest_projection else None,
                result.latest_intelligence.score_id if result.latest_intelligence else None,
            )
            return result
        except ProductNotFoundError:
            raise
        except (
            ProductRepositoryError,
            CatalogProjectionRepositoryError,
            ProductIntelligenceScoreRepositoryError,
            CatalogEnrichmentRepositoryError,
            CatalogExportRepositoryError,
        ) as exc:
            raise CatalogSearchStorageUnavailableError() from exc

    def summarize(self, product: Product) -> CatalogProductSummary:
        try:
            projection = self._projections.get_latest_by_product_id(product.product_id)
            score_page = self._scores.list_by_product(product.product_id, limit=1)
            score = score_page.items[0] if score_page.items else None
            projection_summary = None
            enrichment_available = export_available = False
            if projection is not None:
                readiness = evaluate_publishing_readiness_state(
                    product=product, projection=projection
                )
                projection_summary = CatalogProjectionSummary(
                    projection_id=projection.projection_id,
                    status=projection.status,
                    product_version=projection.product_version,
                    warning_reason_codes=projection.warning_reason_codes,
                    blocking_reason_codes=projection.blocking_reason_codes,
                    created_at=projection.created_at,
                    projection_current=readiness.projection_current,
                    eligible_for_ready_to_publish=readiness.eligible_for_ready_to_publish,
                )
                enrichment_available = self._enrichments.exists_for_projection(
                    projection.projection_id
                )
                export_available = (
                    self._exports.get_by_projection_id(projection.projection_id) is not None
                )
            intelligence_summary = None
            if score is not None:
                intelligence_summary = CatalogIntelligenceSummary(
                    score_id=score.score_id,
                    projection_id=score.projection_id,
                    enrichment_id=score.enrichment_id,
                    overall_score_bp=score.overall_score_bp,
                    overall_score_percent=score.overall_score_percent,
                    grade=score.grade,
                    top_improvement_codes=score.top_improvement_codes,
                    strength_codes=score.strength_codes,
                    policy_version=score.policy_version,
                    created_at=score.created_at,
                    intelligence_current=(
                        projection is not None
                        and score.projection_id == projection.projection_id
                        and projection.product_version == product.version
                    ),
                )
            return CatalogProductSummary(
                product_id=product.product_id,
                name=product.name,
                manufacturer=product.manufacturer,
                model_number=product.model_number,
                category=product.category,
                status=product.status,
                product_version=product.version,
                created_at=product.created_at,
                updated_at=product.updated_at,
                latest_projection=projection_summary,
                latest_intelligence=intelligence_summary,
                enrichment_available=enrichment_available,
                export_available=export_available,
            )
        except CatalogSearchStorageUnavailableError:
            raise
        except (
            CatalogProjectionRepositoryError,
            ProductIntelligenceScoreRepositoryError,
            CatalogEnrichmentRepositoryError,
            CatalogExportRepositoryError,
        ) as exc:
            raise CatalogSearchStorageUnavailableError() from exc
