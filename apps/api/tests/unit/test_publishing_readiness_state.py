"""Pure current publishing-readiness state tests."""

from dataclasses import replace

import pytest

from app.domain.catalog_projection import CatalogBlockingReason, CatalogProjectionStatus
from app.domain.products import ProductStatus
from app.services.publishing_readiness_state import evaluate_publishing_readiness_state
from tests.fixtures.catalog_projection import projected_result


def test_current_ready_review_required_product_is_eligible() -> None:
    product, _, projection = projected_result()
    state = evaluate_publishing_readiness_state(product=product, projection=projection)
    assert state.projection_current is True
    assert state.eligible_for_ready_to_publish is True
    assert state.current_product_version == product.version
    assert state.current_product_status is ProductStatus.REVIEW_REQUIRED


def test_ready_with_warnings_is_eligible_and_preserves_warnings() -> None:
    product, _, projection = projected_result(manufacturer=None)
    state = evaluate_publishing_readiness_state(product=product, projection=projection)
    assert projection.status is CatalogProjectionStatus.READY_WITH_WARNINGS
    assert state.eligible_for_ready_to_publish is True
    assert state.warning_reason_codes == projection.warning_reason_codes


def test_stale_projection_is_described_as_ineligible() -> None:
    product, _, projection = projected_result()
    state = evaluate_publishing_readiness_state(
        product=replace(product, version=4), projection=projection
    )
    assert state.projection_current is False
    assert state.eligible_for_ready_to_publish is False


def test_blocked_projection_is_described_as_ineligible() -> None:
    product, _, projection = projected_result()
    blocked = replace(
        projection,
        status=CatalogProjectionStatus.BLOCKED,
        blocking_reason_codes=(CatalogBlockingReason.REQUIRED_ATTRIBUTE_MISSING,),
    )
    state = evaluate_publishing_readiness_state(product=product, projection=blocked)
    assert state.projection_current is True
    assert state.eligible_for_ready_to_publish is False
    assert state.blocking_reason_codes == blocked.blocking_reason_codes


@pytest.mark.parametrize(
    "status",
    [
        ProductStatus.DRAFT,
        ProductStatus.PROCESSING,
        ProductStatus.FAILED,
        ProductStatus.READY_TO_PUBLISH,
    ],
)
def test_non_review_status_is_not_eligible(status: ProductStatus) -> None:
    product, _, projection = projected_result()
    state = evaluate_publishing_readiness_state(
        product=replace(product, status=status), projection=projection
    )
    assert state.eligible_for_ready_to_publish is False
