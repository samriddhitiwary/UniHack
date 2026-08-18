"""Pure current-state evaluation for one persisted catalog projection."""

from dataclasses import dataclass
from uuid import UUID

from app.domain.catalog_projection import (
    CatalogBlockingReason,
    CatalogProjectionStatus,
    CatalogWarningReason,
    CommerceCatalogProjection,
)
from app.domain.products import Product, ProductStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class PublishingReadinessState:
    product_id: UUID
    projection_id: UUID
    projection_status: CatalogProjectionStatus
    blocking_reason_codes: tuple[CatalogBlockingReason, ...]
    warning_reason_codes: tuple[CatalogWarningReason, ...]
    product_version_at_projection: int
    current_product_version: int
    projection_current: bool
    eligible_for_ready_to_publish: bool
    current_product_status: ProductStatus


def evaluate_publishing_readiness_state(
    *, product: Product, projection: CommerceCatalogProjection
) -> PublishingReadinessState:
    """Compare immutable projection lineage to current Product state without persistence."""
    current = (
        projection.product_id == product.product_id
        and projection.product_version == product.version
    )
    eligible = (
        current
        and projection.status
        in {CatalogProjectionStatus.READY, CatalogProjectionStatus.READY_WITH_WARNINGS}
        and product.status is ProductStatus.REVIEW_REQUIRED
    )
    return PublishingReadinessState(
        product_id=product.product_id,
        projection_id=projection.projection_id,
        projection_status=projection.status,
        blocking_reason_codes=projection.blocking_reason_codes,
        warning_reason_codes=projection.warning_reason_codes,
        product_version_at_projection=projection.product_version,
        current_product_version=product.version,
        projection_current=current,
        eligible_for_ready_to_publish=eligible,
        current_product_status=product.status,
    )
