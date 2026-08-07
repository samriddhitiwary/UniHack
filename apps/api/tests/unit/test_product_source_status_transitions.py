"""Product-source status transition policy tests."""

import pytest

from app.domain.product_sources import ProductSourceStatus, is_status_transition_allowed


@pytest.mark.parametrize(
    ("current", "requested"),
    [
        (ProductSourceStatus.PENDING, ProductSourceStatus.READY),
        (ProductSourceStatus.PENDING, ProductSourceStatus.FAILED),
        (ProductSourceStatus.READY, ProductSourceStatus.PROCESSING),
        (ProductSourceStatus.READY, ProductSourceStatus.FAILED),
        (ProductSourceStatus.PROCESSING, ProductSourceStatus.COMPLETED),
        (ProductSourceStatus.PROCESSING, ProductSourceStatus.FAILED),
        (ProductSourceStatus.FAILED, ProductSourceStatus.READY),
    ],
)
def test_approved_status_transition(
    current: ProductSourceStatus, requested: ProductSourceStatus
) -> None:
    assert is_status_transition_allowed(current, requested)


@pytest.mark.parametrize("status", list(ProductSourceStatus))
def test_same_status_write_is_allowed(status: ProductSourceStatus) -> None:
    assert is_status_transition_allowed(status, status)


@pytest.mark.parametrize(
    ("current", "requested"),
    [
        (ProductSourceStatus.PENDING, ProductSourceStatus.PROCESSING),
        (ProductSourceStatus.PENDING, ProductSourceStatus.COMPLETED),
        (ProductSourceStatus.READY, ProductSourceStatus.COMPLETED),
        (ProductSourceStatus.PROCESSING, ProductSourceStatus.READY),
        (ProductSourceStatus.COMPLETED, ProductSourceStatus.READY),
        (ProductSourceStatus.COMPLETED, ProductSourceStatus.PROCESSING),
        (ProductSourceStatus.COMPLETED, ProductSourceStatus.FAILED),
        (ProductSourceStatus.FAILED, ProductSourceStatus.PROCESSING),
        (ProductSourceStatus.FAILED, ProductSourceStatus.COMPLETED),
    ],
)
def test_rejected_status_transition(
    current: ProductSourceStatus, requested: ProductSourceStatus
) -> None:
    assert not is_status_transition_allowed(current, requested)
