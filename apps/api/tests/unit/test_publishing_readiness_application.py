"""Publishing-readiness application service tests."""

from dataclasses import replace
from typing import cast
from uuid import UUID, uuid4

import pytest

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
    CatalogBlockingReason,
    CatalogProjectionStatus,
    CommerceCatalogProjection,
)
from app.domain.products import Product, ProductPage, ProductStatus
from app.repositories.catalog_projection import CommerceCatalogProjectionRepository
from app.repositories.products import ProductRepository
from app.services.publishing_readiness_application import (
    PublishingReadinessApplicationService,
)
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.catalog_projection import projected_result


class MemoryProducts:
    def __init__(self, product: Product | None, transition_error: Exception | None = None) -> None:
        self.product = product
        self.transition_error = transition_error
        self.transition_calls: list[tuple[UUID, int, ProductStatus]] = []

    def get_by_id(self, product_id: UUID) -> Product | None:
        return self.product if self.product and self.product.product_id == product_id else None

    def mark_ready_to_publish(
        self, *, product_id: UUID, expected_version: int, expected_status: ProductStatus
    ) -> Product:
        self.transition_calls.append((product_id, expected_version, expected_status))
        if self.transition_error:
            raise self.transition_error
        assert self.product is not None
        self.product = replace(
            self.product,
            status=ProductStatus.READY_TO_PUBLISH,
            version=expected_version + 1,
            updated_at=NOW,
        )
        return self.product

    def create(self, product: Product) -> Product:  # pragma: no cover - protocol-only
        return product

    def update(self, product: Product, expected_version: int) -> Product:  # pragma: no cover
        return product

    def list_products(self, *, limit=25, cursor=None) -> ProductPage:  # pragma: no cover
        return ProductPage(items=(), next_cursor=None)

    def list_by_status(self, status, *, limit=25, cursor=None) -> ProductPage:  # pragma: no cover
        return ProductPage(items=(), next_cursor=None)

    def delete(self, product_id, expected_version):  # pragma: no cover
        return None


class MemoryProjections:
    def __init__(self, projection: CommerceCatalogProjection | None) -> None:
        self.projection = projection

    def get_by_id(self, projection_id: UUID) -> CommerceCatalogProjection | None:
        return (
            self.projection
            if self.projection and self.projection.projection_id == projection_id
            else None
        )

    def create(self, result):  # pragma: no cover - protocol-only
        return result

    def get_by_job_id(self, job_id):  # pragma: no cover
        return None

    def get_by_materialization_id(self, materialization_id):  # pragma: no cover
        return None


def _service(products: MemoryProducts, projections: MemoryProjections):
    return PublishingReadinessApplicationService(
        cast(ProductRepository, products),
        cast(CommerceCatalogProjectionRepository, projections),
    )


def test_ready_projection_applies_atomic_transition() -> None:
    product, _, projection = projected_result()
    products = MemoryProducts(product)
    result = _service(products, MemoryProjections(projection)).apply(
        product_id=product.product_id,
        projection_id=projection.projection_id,
        expected_version=3,
    )
    assert result.previous_status is ProductStatus.REVIEW_REQUIRED
    assert result.status is ProductStatus.READY_TO_PUBLISH
    assert (result.previous_version, result.version) == (3, 4)
    assert result.applied_at == NOW
    assert products.transition_calls == [(product.product_id, 3, ProductStatus.REVIEW_REQUIRED)]


def test_ready_with_warnings_applies_and_preserves_warnings() -> None:
    product, _, projection = projected_result(manufacturer=None)
    result = _service(MemoryProducts(product), MemoryProjections(projection)).apply(
        product_id=product.product_id,
        projection_id=projection.projection_id,
        expected_version=3,
    )
    assert result.projection_status is CatalogProjectionStatus.READY_WITH_WARNINGS
    assert result.warning_reason_codes == projection.warning_reason_codes


def test_blocked_projection_is_rejected_without_mutation() -> None:
    product, _, projection = projected_result()
    blocked = replace(
        projection,
        status=CatalogProjectionStatus.BLOCKED,
        blocking_reason_codes=(CatalogBlockingReason.REQUIRED_ATTRIBUTE_INVALID,),
    )
    products = MemoryProducts(product)
    with pytest.raises(PublishingReadinessBlockedError) as captured:
        _service(products, MemoryProjections(blocked)).apply(
            product_id=product.product_id,
            projection_id=blocked.projection_id,
            expected_version=3,
        )
    assert captured.value.blocking_reason_codes == ("REQUIRED_ATTRIBUTE_INVALID",)
    assert products.transition_calls == []


def test_stale_request_and_stale_projection_are_independent() -> None:
    product, _, projection = projected_result()
    service = _service(MemoryProducts(product), MemoryProjections(projection))
    with pytest.raises(ProductVersionConflictError):
        service.apply(
            product_id=product.product_id,
            projection_id=projection.projection_id,
            expected_version=2,
        )
    changed = replace(product, version=4)
    with pytest.raises(PublishingReadinessProductChangedError):
        _service(MemoryProducts(changed), MemoryProjections(projection)).apply(
            product_id=product.product_id,
            projection_id=projection.projection_id,
            expected_version=4,
        )


def test_missing_resources_and_cross_product_are_controlled() -> None:
    product, _, projection = projected_result()
    with pytest.raises(ProductNotFoundError):
        _service(MemoryProducts(None), MemoryProjections(projection)).apply(
            product_id=product.product_id,
            projection_id=projection.projection_id,
            expected_version=3,
        )
    with pytest.raises(CatalogProjectionNotFoundError):
        _service(MemoryProducts(product), MemoryProjections(None)).apply(
            product_id=product.product_id,
            projection_id=uuid4(),
            expected_version=3,
        )
    other = replace(projection, product_id=uuid4())
    with pytest.raises(PublishingReadinessCrossProductProjectionError):
        _service(MemoryProducts(product), MemoryProjections(other)).apply(
            product_id=product.product_id,
            projection_id=other.projection_id,
            expected_version=3,
        )


@pytest.mark.parametrize(
    "status",
    [ProductStatus.DRAFT, ProductStatus.PROCESSING, ProductStatus.FAILED],
)
def test_forbidden_product_statuses_are_rejected(status: ProductStatus) -> None:
    product, _, projection = projected_result()
    products = MemoryProducts(replace(product, status=status))
    with pytest.raises(PublishingReadinessStatusTransitionNotAllowedError) as captured:
        _service(products, MemoryProjections(projection)).apply(
            product_id=product.product_id,
            projection_id=projection.projection_id,
            expected_version=3,
        )
    assert captured.value.current_status == status.value
    assert products.transition_calls == []


def test_already_ready_is_conflict_and_does_not_advance_version() -> None:
    product, _, projection = projected_result()
    products = MemoryProducts(replace(product, status=ProductStatus.READY_TO_PUBLISH))
    with pytest.raises(ProductAlreadyReadyToPublishError):
        _service(products, MemoryProjections(projection)).apply(
            product_id=product.product_id,
            projection_id=projection.projection_id,
            expected_version=3,
        )
    assert products.transition_calls == []


def test_conditional_race_status_is_mapped_without_retry() -> None:
    product, _, projection = projected_result()
    products = MemoryProducts(product, ProductStatusConflictError(ProductStatus.FAILED.value))
    with pytest.raises(PublishingReadinessStatusTransitionNotAllowedError):
        _service(products, MemoryProjections(projection)).apply(
            product_id=product.product_id,
            projection_id=projection.projection_id,
            expected_version=3,
        )
    assert len(products.transition_calls) == 1


def test_reads_isolate_cross_product_projection_and_do_not_mutate() -> None:
    product, _, projection = projected_result()
    products = MemoryProducts(product)
    service = _service(products, MemoryProjections(projection))
    assert (
        service.get_catalog_projection(
            product_id=product.product_id, projection_id=projection.projection_id
        )
        is projection
    )
    state = service.get_publishing_readiness(
        product_id=product.product_id, projection_id=projection.projection_id
    )
    assert state.eligible_for_ready_to_publish is True
    assert products.transition_calls == []
    other = replace(projection, product_id=uuid4())
    with pytest.raises(CatalogProjectionNotFoundError):
        _service(products, MemoryProjections(other)).get_catalog_projection(
            product_id=product.product_id, projection_id=other.projection_id
        )
