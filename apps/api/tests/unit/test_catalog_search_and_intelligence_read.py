"""SPEC-036 catalog search, summary, and intelligence read tests."""

# mypy: disable-error-code="no-untyped-def,no-untyped-call,arg-type"

from dataclasses import replace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import (
    CatalogSearchFilterCombinationUnsupportedError,
    ProductIntelligenceScoreNotFoundError,
    ProductNotFoundError,
)
from app.domain.catalog_search import (
    CatalogProductSearchQuery,
    CatalogSearchAccessPattern,
    normalize_catalog_search_text,
)
from app.domain.product_intelligence import ProductIntelligenceScorePage
from app.domain.products import ProductCategory, ProductPage, ProductStatus
from app.services.catalog_search import CatalogSearchService
from app.services.catalog_summary import CatalogSummaryService
from app.services.product_intelligence_read import ProductIntelligenceReadService
from tests.fixtures.catalog_projection import projected_result
from tests.unit.test_product_intelligence import score_result


@pytest.mark.parametrize(
    ("query", "pattern"),
    [
        ({}, CatalogSearchAccessPattern.CREATED_AT),
        ({"status": ProductStatus.DRAFT}, CatalogSearchAccessPattern.STATUS),
        (
            {"category": ProductCategory.INDUCTION_MOTOR},
            CatalogSearchAccessPattern.CATEGORY,
        ),
        (
            {
                "category": ProductCategory.INDUCTION_MOTOR,
                "status": ProductStatus.DRAFT,
            },
            CatalogSearchAccessPattern.CATEGORY_STATUS,
        ),
        ({"manufacturer": "  ACME   Works "}, CatalogSearchAccessPattern.MANUFACTURER),
        ({"model_number": " MX-1 "}, CatalogSearchAccessPattern.MODEL_NUMBER),
        ({"name_prefix": " Industrial  "}, CatalogSearchAccessPattern.NAME_PREFIX),
    ],
)
def test_catalog_search_query_selects_only_supported_access_patterns(query, pattern) -> None:
    assert CatalogProductSearchQuery(**query).plan() is pattern


@pytest.mark.parametrize(
    "query",
    [
        {"category": ProductCategory.INDUCTION_MOTOR, "manufacturer": "acme"},
        {"name_prefix": "motor", "status": ProductStatus.DRAFT},
        {"publishing_readiness": "READY"},
        {"intelligence_grade": "EXCELLENT"},
        {"min_intelligence_score": 50},
        {"max_intelligence_score": 80},
    ],
)
def test_catalog_search_query_rejects_non_indexed_filters(query) -> None:
    assert CatalogProductSearchQuery(**query).plan() is None


def test_catalog_search_normalization_and_bounds() -> None:
    assert normalize_catalog_search_text("  ACME\t Heavy   Works ") == "acme heavy works"
    query = CatalogProductSearchQuery(manufacturer="  ACME   Works ")
    assert query.manufacturer == "acme works"
    with pytest.raises(ValueError):
        CatalogProductSearchQuery(name_prefix="   ")
    with pytest.raises(ValueError):
        CatalogProductSearchQuery(limit=101)
    with pytest.raises(ValueError):
        CatalogProductSearchQuery(min_intelligence_score=80, max_intelligence_score=20)


def test_catalog_search_service_dispatches_without_scanning() -> None:
    product, _, _ = projected_result()
    products = MagicMock()
    products.list_by_category_status.return_value = ProductPage((product,), "next")
    summaries = MagicMock()
    summaries.summarize.return_value = MagicMock(product_id=product.product_id)
    service = CatalogSearchService(products, summaries)

    result = service.search(
        CatalogProductSearchQuery(category=product.category, status=product.status, limit=7)
    )

    products.list_by_category_status.assert_called_once_with(
        product.category, product.status, limit=7, cursor=None
    )
    assert result.next_cursor == "next"
    assert len(result.items) == 1
    assert all(call[0] != "scan" for call in products.method_calls)


def test_catalog_search_service_rejects_unsupported_combination() -> None:
    service = CatalogSearchService(MagicMock(), MagicMock())
    with pytest.raises(CatalogSearchFilterCombinationUnsupportedError):
        service.search(
            CatalogProductSearchQuery(
                status=ProductStatus.DRAFT,
                manufacturer="acme",
            )
        )


def _summary_service(product, projection, score):
    products = MagicMock()
    products.get_by_id.return_value = product
    projections = MagicMock()
    projections.get_latest_by_product_id.return_value = projection
    scores = MagicMock()
    scores.list_by_product.return_value = ProductIntelligenceScorePage(
        items=(score,) if score else (), next_cursor=None
    )
    enrichments = MagicMock()
    enrichments.exists_for_projection.return_value = True
    exports = MagicMock()
    exports.get_by_projection_id.return_value = MagicMock()
    return CatalogSummaryService(
        product_repository=products,
        projection_repository=projections,
        score_repository=scores,
        enrichment_repository=enrichments,
        export_repository=exports,
    )


def test_catalog_summary_reports_current_lineage_and_availability() -> None:
    score = score_result()
    product, _, projection = projected_result()
    product = replace(product, product_id=score.product_id)
    projection = replace(
        projection,
        product_id=product.product_id,
        product_version=product.version,
        projection_id=score.projection_id,
    )
    result = _summary_service(product, projection, score).get_for_product(product.product_id)

    assert result.latest_projection is not None
    assert result.latest_projection.projection_current is True
    assert result.latest_intelligence is not None
    assert result.latest_intelligence.intelligence_current is True
    assert result.enrichment_available is True
    assert result.export_available is True


def test_catalog_summary_handles_missing_and_stale_artifacts() -> None:
    product, _, projection = projected_result()
    missing = _summary_service(product, None, None).summarize(product)
    assert missing.latest_projection is None
    assert missing.latest_intelligence is None
    assert missing.enrichment_available is False
    stale = _summary_service(product, replace(projection, product_version=2), None).summarize(
        product
    )
    assert stale.latest_projection is not None
    assert stale.latest_projection.projection_current is False


def test_catalog_summary_requires_product() -> None:
    service = _summary_service(None, None, None)
    with pytest.raises(ProductNotFoundError):
        service.get_for_product(uuid4())


def test_product_intelligence_read_enforces_product_ownership_and_history() -> None:
    score = score_result()
    products = MagicMock()
    products.get_by_id.return_value = MagicMock()
    scores = MagicMock()
    scores.get_by_id.return_value = score
    scores.list_by_product.return_value = ProductIntelligenceScorePage((score,), "cursor")
    service = ProductIntelligenceReadService(products, scores)

    assert service.get_score(score.product_id, score.score_id) == score
    assert service.list_history(score.product_id, limit=1).next_cursor == "cursor"
    with pytest.raises(ProductIntelligenceScoreNotFoundError):
        service.get_score(uuid4(), score.score_id)


def test_product_intelligence_read_returns_product_not_found_first() -> None:
    products = MagicMock()
    products.get_by_id.return_value = None
    scores = MagicMock()
    service = ProductIntelligenceReadService(products, scores)
    with pytest.raises(ProductNotFoundError):
        service.list_history(uuid4())
    scores.list_by_product.assert_not_called()
