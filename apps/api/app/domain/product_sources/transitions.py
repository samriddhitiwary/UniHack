"""Explicit product-source status transition policy."""

from app.domain.product_sources.enums import ProductSourceStatus

_ALLOWED_TRANSITIONS: dict[ProductSourceStatus, frozenset[ProductSourceStatus]] = {
    ProductSourceStatus.PENDING: frozenset({ProductSourceStatus.READY, ProductSourceStatus.FAILED}),
    ProductSourceStatus.READY: frozenset(
        {ProductSourceStatus.PROCESSING, ProductSourceStatus.FAILED}
    ),
    ProductSourceStatus.PROCESSING: frozenset(
        {ProductSourceStatus.COMPLETED, ProductSourceStatus.FAILED}
    ),
    ProductSourceStatus.FAILED: frozenset({ProductSourceStatus.READY}),
    ProductSourceStatus.COMPLETED: frozenset(),
}


def is_status_transition_allowed(
    current: ProductSourceStatus,
    requested: ProductSourceStatus,
) -> bool:
    """Return whether a direct transition or same-status write is approved."""
    return requested is current or requested in _ALLOWED_TRANSITIONS[current]
