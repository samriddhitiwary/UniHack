"""Synchronous catalog reads and optimistic publishing-readiness application."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Never
from uuid import UUID

from app.core.exceptions import (
    CatalogProjectionNotFoundError,
    ProductAlreadyReadyToPublishError,
    ProductNotFoundError,
    ProductStatusConflictError,
    ProductVersionConflictError,
    PublishingReadinessBlockedError,
    PublishingReadinessCrossProductProjectionError,
    PublishingReadinessProductChangedError,
    PublishingReadinessStatusTransitionNotAllowedError,
)
from app.domain.catalog_projection import (
    CatalogProjectionStatus,
    CatalogWarningReason,
    CommerceCatalogProjection,
)
from app.domain.products import Product, ProductStatus
from app.repositories.catalog_projection import CommerceCatalogProjectionRepository
from app.repositories.products import ProductRepository
from app.services.publishing_readiness_state import (
    PublishingReadinessState,
    evaluate_publishing_readiness_state,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class PublishingReadinessApplicationResult:
    product_id: UUID
    projection_id: UUID
    projection_status: CatalogProjectionStatus
    previous_status: ProductStatus
    status: ProductStatus
    previous_version: int
    version: int
    applied_at: datetime
    warning_reason_codes: tuple[CatalogWarningReason, ...]


class PublishingReadinessApplicationService:
    """Coordinate SPEC-032 operations without FastAPI or DynamoDB coupling."""

    def __init__(
        self,
        product_repository: ProductRepository,
        projection_repository: CommerceCatalogProjectionRepository,
    ) -> None:
        self._products = product_repository
        self._projections = projection_repository

    def get_catalog_projection(
        self, *, product_id: UUID, projection_id: UUID
    ) -> CommerceCatalogProjection:
        self._load_product(product_id)
        projection = self._load_projection(projection_id)
        if projection.product_id != product_id:
            raise CatalogProjectionNotFoundError(projection_id)
        logger.info(
            "event=catalog_projection.read product_id=%s projection_id=%s status=%s",
            product_id,
            projection_id,
            projection.status.value,
        )
        return projection

    def get_publishing_readiness(
        self, *, product_id: UUID, projection_id: UUID
    ) -> PublishingReadinessState:
        product = self._load_product(product_id)
        projection = self._load_projection(projection_id)
        if projection.product_id != product_id:
            raise CatalogProjectionNotFoundError(projection_id)
        state = evaluate_publishing_readiness_state(product=product, projection=projection)
        logger.info(
            "event=catalog_projection.readiness_read product_id=%s projection_id=%s "
            "projection_status=%s product_status=%s product_version=%s current=%s eligible=%s",
            product_id,
            projection_id,
            projection.status.value,
            product.status.value,
            product.version,
            state.projection_current,
            state.eligible_for_ready_to_publish,
        )
        return state

    def apply(
        self, *, product_id: UUID, projection_id: UUID, expected_version: int
    ) -> PublishingReadinessApplicationResult:
        product = self._load_product(product_id)
        projection = self._load_projection(projection_id)
        logger.info(
            "event=publishing_readiness.apply_started product_id=%s projection_id=%s "
            "product_version=%s product_status=%s projection_status=%s",
            product_id,
            projection_id,
            product.version,
            product.status.value,
            projection.status.value,
        )
        if projection.product_id != product_id:
            raise PublishingReadinessCrossProductProjectionError()
        if projection.status is CatalogProjectionStatus.BLOCKED:
            logger.info(
                "event=publishing_readiness.blocked product_id=%s projection_id=%s blockers=%s",
                product_id,
                projection_id,
                len(projection.blocking_reason_codes),
            )
            raise PublishingReadinessBlockedError(
                tuple(reason.value for reason in projection.blocking_reason_codes)
            )
        if expected_version != product.version:
            logger.info(
                "event=publishing_readiness.version_conflict product_id=%s projection_id=%s "
                "expected_version=%s",
                product_id,
                projection_id,
                expected_version,
            )
            raise ProductVersionConflictError("request Product version is stale")
        if projection.product_version != product.version:
            logger.info(
                "event=publishing_readiness.stale_projection product_id=%s projection_id=%s",
                product_id,
                projection_id,
            )
            raise PublishingReadinessProductChangedError()
        self._validate_source_status(product)
        try:
            updated = self._products.mark_ready_to_publish(
                product_id=product_id,
                expected_version=expected_version,
                expected_status=ProductStatus.REVIEW_REQUIRED,
            )
        except ProductStatusConflictError as exc:
            self._raise_status_error(exc.current_status)
        except ProductVersionConflictError:
            logger.info(
                "event=publishing_readiness.version_conflict product_id=%s projection_id=%s "
                "expected_version=%s",
                product_id,
                projection_id,
                expected_version,
            )
            raise
        logger.info(
            "event=publishing_readiness.applied product_id=%s projection_id=%s "
            "projection_status=%s product_version=%s warning_count=%s",
            product_id,
            projection_id,
            projection.status.value,
            updated.version,
            len(projection.warning_reason_codes),
        )
        return PublishingReadinessApplicationResult(
            product_id=updated.product_id,
            projection_id=projection.projection_id,
            projection_status=projection.status,
            previous_status=product.status,
            status=updated.status,
            previous_version=product.version,
            version=updated.version,
            applied_at=updated.updated_at,
            warning_reason_codes=projection.warning_reason_codes,
        )

    def _load_product(self, product_id: UUID) -> Product:
        product = self._products.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        return product

    def _load_projection(self, projection_id: UUID) -> CommerceCatalogProjection:
        projection = self._projections.get_by_id(projection_id)
        if projection is None:
            raise CatalogProjectionNotFoundError(projection_id)
        return projection

    @staticmethod
    def _validate_source_status(product: Product) -> None:
        if product.status is ProductStatus.READY_TO_PUBLISH:
            raise ProductAlreadyReadyToPublishError()
        if product.status is not ProductStatus.REVIEW_REQUIRED:
            logger.info(
                "event=publishing_readiness.transition_rejected product_id=%s product_status=%s",
                product.product_id,
                product.status.value,
            )
            raise PublishingReadinessStatusTransitionNotAllowedError(product.status.value)

    @staticmethod
    def _raise_status_error(current_status: str) -> Never:
        if current_status == ProductStatus.READY_TO_PUBLISH.value:
            raise ProductAlreadyReadyToPublishError()
        raise PublishingReadinessStatusTransitionNotAllowedError(current_status)
