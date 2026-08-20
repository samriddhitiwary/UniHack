"""SPEC-036 public read API contract tests."""

# mypy: disable-error-code="no-untyped-def,no-untyped-call,arg-type"

from dataclasses import replace

from fastapi.testclient import TestClient

from app.api.dependencies.catalog_search import (
    get_catalog_search_service,
    get_catalog_summary_service,
    get_product_intelligence_read_service,
)
from app.core.exceptions import (
    CatalogSearchFilterCombinationUnsupportedError,
    ProductIntelligenceScoreNotFoundError,
)
from app.domain.catalog_search import CatalogProductSearchPage, CatalogProductSummary
from app.domain.product_intelligence import ProductIntelligenceScorePage
from app.main import app
from tests.fixtures.catalog_projection import projected_result
from tests.unit.test_product_intelligence import score_result


def _summary() -> CatalogProductSummary:
    product, _, _ = projected_result()
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
        latest_projection=None,
        latest_intelligence=None,
        enrichment_available=False,
        export_available=False,
    )


class SearchApiService:
    def __init__(self, summary: CatalogProductSummary) -> None:
        self.summary = summary
        self.last_query = None

    def search(self, query):
        self.last_query = query
        if query.plan() is None:
            raise CatalogSearchFilterCombinationUnsupportedError()
        return CatalogProductSearchPage((self.summary,), "next-page")


class SummaryApiService:
    def __init__(self, summary: CatalogProductSummary) -> None:
        self.summary = summary

    def get_for_product(self, product_id):
        return replace(self.summary, product_id=product_id)


class IntelligenceApiService:
    def __init__(self, score) -> None:
        self.score = score

    def list_history(self, product_id, *, limit=20, cursor=None):
        return ProductIntelligenceScorePage((self.score,), "score-page")

    def get_score(self, product_id, score_id):
        if product_id != self.score.product_id or score_id != self.score.score_id:
            raise ProductIntelligenceScoreNotFoundError(product_id, score_id)
        return self.score


def test_catalog_search_and_summary_contract(client: TestClient) -> None:
    summary = _summary()
    search = SearchApiService(summary)
    app.dependency_overrides[get_catalog_search_service] = lambda: search
    app.dependency_overrides[get_catalog_summary_service] = lambda: SummaryApiService(summary)

    response = client.get(
        "/api/v1/catalog/products",
        params={"manufacturer": "  CatalogIQ   Manufacturing ", "limit": 1},
        headers={"X-Request-ID": "spec-036-search"},
    )
    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    assert response.json()["items"][0]["productId"] == str(summary.product_id)
    assert response.json()["items"][0]["intelligenceScorePercent"] is None
    assert response.json()["nextCursor"] == "next-page"
    assert search.last_query.manufacturer == "catalogiq manufacturing"

    detail = client.get(f"/api/v1/products/{summary.product_id}/catalog-summary")
    assert detail.status_code == 200
    assert detail.json()["version"] == summary.product_version
    assert detail.json()["latestProjection"] is None


def test_catalog_search_validation_and_unsupported_filters(client: TestClient) -> None:
    search = SearchApiService(_summary())
    app.dependency_overrides[get_catalog_search_service] = lambda: search

    invalid = client.get("/api/v1/catalog/products", params={"limit": 0})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"
    blank = client.get("/api/v1/catalog/products", params={"namePrefix": "   "})
    assert blank.status_code == 422
    unsupported = client.get(
        "/api/v1/catalog/products", params={"namePrefix": "motor", "status": "DRAFT"}
    )
    assert unsupported.status_code == 422
    assert unsupported.json()["error"]["code"] == ("CATALOG_SEARCH_FILTER_COMBINATION_UNSUPPORTED")


def test_intelligence_history_detail_and_cross_product_404(client: TestClient) -> None:
    score = score_result()
    service = IntelligenceApiService(score)
    app.dependency_overrides[get_product_intelligence_read_service] = lambda: service

    history = client.get(
        f"/api/v1/products/{score.product_id}/intelligence-scores", params={"limit": 1}
    )
    assert history.status_code == 200
    assert history.json()["items"][0]["overallScorePercent"] == score.overall_score_percent
    assert history.json()["nextCursor"] == "score-page"

    detail = client.get(f"/api/v1/products/{score.product_id}/intelligence-scores/{score.score_id}")
    assert detail.status_code == 200
    assert len(detail.json()["components"]) == 6
    assert detail.json()["scoreId"] == str(score.score_id)

    hidden = client.get(
        f"/api/v1/products/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/"
        f"intelligence-scores/{score.score_id}"
    )
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "PRODUCT_INTELLIGENCE_SCORE_NOT_FOUND"
