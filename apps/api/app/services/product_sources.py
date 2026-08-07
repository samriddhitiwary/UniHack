"""Product-source application workflows."""

import hashlib
import logging
from dataclasses import replace
from uuid import UUID

from app.core.exceptions import (
    ProductNotFoundError,
    ProductRepositoryError,
    ProductSourceRepositoryError,
)
from app.domain.product_sources import ProductSource, ProductSourceStatus, ProductSourceType
from app.repositories.product_sources import ProductSourceRepository
from app.repositories.products import ProductRepository
from app.schemas.product_sources import TextProductSourceCreate

logger = logging.getLogger(__name__)


class ProductSourceService:
    """Coordinate product-source use cases without HTTP or infrastructure coupling."""

    def __init__(
        self,
        product_repository: ProductRepository,
        source_repository: ProductSourceRepository,
    ) -> None:
        self._product_repository = product_repository
        self._source_repository = source_repository

    def create_text_source(
        self,
        product_id: UUID,
        request: TextProductSourceCreate,
    ) -> ProductSource:
        """Attach normalized plain text to an existing product."""
        content = request.text_content.encode("utf-8")
        logger.info(
            "event=product_source.text_create.requested product_id=%s "
            "size_bytes=%s has_display_name=%s",
            product_id,
            len(content),
            request.display_name is not None,
        )
        try:
            product = self._product_repository.get_by_id(product_id)
        except ProductRepositoryError as exc:
            logger.warning(
                "event=product_source.text_create_failed product_id=%s error_type=%s",
                product_id,
                type(exc).__name__,
            )
            raise
        if product is None:
            logger.info(
                "event=product_source.parent_product_not_found product_id=%s",
                product_id,
            )
            raise ProductNotFoundError(product_id)

        source = ProductSource.create(
            product_id=product_id,
            source_type=ProductSourceType.TEXT,
            original_filename=None,
            storage_key=None,
            mime_type="text/plain",
            file_size_bytes=len(content),
            checksum_sha256=hashlib.sha256(content).hexdigest(),
            display_name=request.display_name,
            text_content=request.text_content,
        )
        source = replace(source, status=ProductSourceStatus.READY)
        try:
            stored = self._source_repository.create(source)
        except ProductSourceRepositoryError as exc:
            logger.warning(
                "event=product_source.text_create_failed product_id=%s source_id=%s error_type=%s",
                product_id,
                source.source_id,
                type(exc).__name__,
            )
            raise
        logger.info(
            "event=product_source.text_created product_id=%s source_id=%s "
            "source_type=%s size_bytes=%s",
            stored.product_id,
            stored.source_id,
            stored.source_type.value,
            stored.file_size_bytes,
        )
        return stored
