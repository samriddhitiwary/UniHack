"""Product application service."""

import logging
from dataclasses import replace
from uuid import UUID

from app.core.exceptions import ProductNotFoundError, ProductVersionConflictError
from app.domain.products import Product, ProductStatus
from app.repositories.products import ProductRepository
from app.schemas.products import ProductCreate, ProductListResult, ProductRecord, ProductUpdate

logger = logging.getLogger(__name__)


class ProductService:
    """Coordinate product use cases without HTTP or persistence coupling."""

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    def create_product(self, request: ProductCreate) -> Product:
        product = Product.create(
            name=request.name,
            manufacturer=request.manufacturer,
            model_number=request.model_number,
            category=request.category,
            description=request.description,
        )
        stored = self._repository.create(product)
        logger.info(
            "event=product.created product_id=%s category=%s",
            stored.product_id,
            stored.category.value,
        )
        return stored

    def get_product(self, product_id: UUID) -> Product:
        product = self._repository.get_by_id(product_id)
        if product is None:
            logger.info("event=product.not_found product_id=%s", product_id)
            raise ProductNotFoundError(product_id)
        logger.info("event=product.retrieved product_id=%s", product_id)
        return product

    def list_products(
        self,
        *,
        limit: int,
        cursor: str | None = None,
        status: ProductStatus | None = None,
    ) -> ProductListResult:
        logger.info(
            "event=product.list.requested limit=%s status=%s has_cursor=%s",
            limit,
            status.value if status is not None else None,
            cursor is not None,
        )
        if status is None:
            page = self._repository.list_products(limit=limit, cursor=cursor)
        else:
            page = self._repository.list_by_status(status, limit=limit, cursor=cursor)
        result = ProductListResult(
            items=[ProductRecord.model_validate(product) for product in page.items],
            next_cursor=page.next_cursor,
        )
        logger.info(
            "event=product.list.completed limit=%s status=%s result_count=%s has_next_cursor=%s",
            limit,
            status.value if status is not None else None,
            len(result.items),
            result.next_cursor is not None,
        )
        return result

    def update_product(self, product_id: UUID, request: ProductUpdate) -> Product:
        updated_fields = request.model_fields_set & request.editable_fields
        logger.info(
            "event=product.update.requested product_id=%s expected_version=%s fields=%s",
            product_id,
            request.version,
            ",".join(sorted(updated_fields)),
        )
        current = self._repository.get_by_id(product_id)
        if current is None:
            logger.info("event=product.update_not_found product_id=%s", product_id)
            raise ProductNotFoundError(product_id)
        changes = request.model_dump(
            include=updated_fields,
            exclude_unset=True,
            by_alias=False,
        )
        candidate = replace(current, **changes)
        try:
            stored = self._repository.update(candidate, expected_version=request.version)
        except ProductVersionConflictError:
            logger.info(
                "event=product.update_version_conflict product_id=%s expected_version=%s",
                product_id,
                request.version,
            )
            raise
        logger.info(
            "event=product.updated product_id=%s version=%s status=%s fields=%s",
            stored.product_id,
            stored.version,
            stored.status.value,
            ",".join(sorted(updated_fields)),
        )
        return stored

    def delete_product(self, product_id: UUID, expected_version: int) -> None:
        logger.info(
            "event=product.delete.requested product_id=%s expected_version=%s",
            product_id,
            expected_version,
        )
        current = self._repository.get_by_id(product_id)
        if current is None:
            logger.info("event=product.delete_not_found product_id=%s", product_id)
            raise ProductNotFoundError(product_id)
        try:
            self._repository.delete(product_id, expected_version)
        except ProductVersionConflictError:
            logger.info(
                "event=product.delete_version_conflict product_id=%s expected_version=%s",
                product_id,
                expected_version,
            )
            raise
        logger.info(
            "event=product.deleted product_id=%s expected_version=%s category=%s",
            product_id,
            expected_version,
            current.category.value,
        )
