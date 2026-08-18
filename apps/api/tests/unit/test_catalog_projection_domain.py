from dataclasses import FrozenInstanceError, replace

import pytest

from app.domain.catalog_projection import (
    CatalogBlockingReason,
    CatalogProjectionStatus,
    CatalogWarningReason,
)
from tests.fixtures.catalog_projection import projected_result


def test_projection_attributes_and_identity_snapshot_are_immutable_and_coherent() -> None:
    _, _, result = projected_result()
    with pytest.raises(FrozenInstanceError):
        result.product_name = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.attributes[0].value = "changed"  # type: ignore[misc]
    with pytest.raises(ValueError):
        replace(result, product_version=0)
    with pytest.raises(ValueError):
        replace(result, attribute_count=result.attribute_count + 1)
    with pytest.raises(ValueError):
        replace(result, required_attribute_count=result.required_attribute_count - 1)


def test_status_and_reason_invariants() -> None:
    _, _, result = projected_result()
    with pytest.raises(ValueError):
        replace(
            result,
            status=CatalogProjectionStatus.BLOCKED,
            blocking_reason_codes=(),
        )
    with pytest.raises(ValueError):
        replace(
            result,
            status=CatalogProjectionStatus.READY,
            warning_reason_codes=(CatalogWarningReason.DESCRIPTION_MISSING,),
        )
    blocked = replace(
        result,
        status=CatalogProjectionStatus.BLOCKED,
        blocking_reason_codes=(CatalogBlockingReason.PRODUCT_NAME_MISSING,),
    )
    assert blocked.status is CatalogProjectionStatus.BLOCKED
