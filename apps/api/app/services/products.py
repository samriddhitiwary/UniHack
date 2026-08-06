"""Product application service."""

import logging
from uuid import UUID

from app.core.exceptions import ProductNotFoundError
from app.domain.products import Product
from app.repositories.products import ProductRepository
from app.schemas.products import ProductCreate

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
