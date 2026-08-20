"""Indexed catalog Product search with bounded summary enrichment."""

import logging

from app.core.exceptions import (
    CatalogSearchFilterCombinationUnsupportedError,
    CatalogSearchStorageUnavailableError,
    ProductRepositoryError,
)
from app.domain.catalog_search import (
    CatalogProductSearchPage,
    CatalogProductSearchQuery,
    CatalogSearchAccessPattern,
)
from app.domain.products import ProductPage
from app.repositories.products import ProductRepository
from app.services.catalog_summary import CatalogSummaryService

logger = logging.getLogger(__name__)


class CatalogSearchService:
    def __init__(
        self, product_repository: ProductRepository, summary_service: CatalogSummaryService
    ) -> None:
        self._products = product_repository
        self._summaries = summary_service

    def search(self, query: CatalogProductSearchQuery) -> CatalogProductSearchPage:
        pattern = query.plan()
        if pattern is None:
            logger.info("event=catalog_search.unsupported_filter")
            raise CatalogSearchFilterCombinationUnsupportedError()
        logger.info(
            "event=catalog_search.requested access_pattern=%s limit=%s", pattern, query.limit
        )
        try:
            page = self._query(pattern, query)
            result = CatalogProductSearchPage(
                items=tuple(self._summaries.summarize(product) for product in page.items),
                next_cursor=page.next_cursor,
            )
        except CatalogSearchStorageUnavailableError:
            raise
        except ProductRepositoryError as exc:
            raise CatalogSearchStorageUnavailableError() from exc
        logger.info(
            "event=catalog_search.completed access_pattern=%s result_count=%s",
            pattern,
            len(result.items),
        )
        return result

    def _query(
        self, pattern: CatalogSearchAccessPattern, query: CatalogProductSearchQuery
    ) -> ProductPage:
        if pattern is CatalogSearchAccessPattern.CREATED_AT:
            return self._products.list_created(limit=query.limit, cursor=query.cursor)
        if pattern is CatalogSearchAccessPattern.STATUS:
            assert query.status is not None
            return self._products.search_by_status(
                query.status, limit=query.limit, cursor=query.cursor
            )
        if pattern is CatalogSearchAccessPattern.CATEGORY:
            assert query.category is not None
            return self._products.list_by_category(
                query.category, limit=query.limit, cursor=query.cursor
            )
        if pattern is CatalogSearchAccessPattern.CATEGORY_STATUS:
            assert query.category is not None and query.status is not None
            return self._products.list_by_category_status(
                query.category, query.status, limit=query.limit, cursor=query.cursor
            )
        if pattern is CatalogSearchAccessPattern.MANUFACTURER:
            assert query.manufacturer is not None
            return self._products.list_by_manufacturer(
                query.manufacturer, limit=query.limit, cursor=query.cursor
            )
        if pattern is CatalogSearchAccessPattern.MODEL_NUMBER:
            assert query.model_number is not None
            return self._products.list_by_model_number(
                query.model_number, limit=query.limit, cursor=query.cursor
            )
        assert query.name_prefix is not None
        return self._products.list_by_name_prefix(
            query.name_prefix, limit=query.limit, cursor=query.cursor
        )
