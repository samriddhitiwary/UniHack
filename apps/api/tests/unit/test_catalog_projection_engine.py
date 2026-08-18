from dataclasses import fields, replace
from types import SimpleNamespace

import pytest

from app.core.exceptions import CatalogProjectionCategoryMismatchError
from app.domain.catalog_projection import CatalogProjectionStatus, CatalogWarningReason
from app.domain.products import ProductCategory
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.catalog_projection import (
    catalog_product,
    projected_result,
    projection_engine,
    reviewed_materialization,
)


@pytest.mark.parametrize("pump", [False, True])
def test_complete_motor_and_pump_are_ready_with_exact_lineage(pump) -> None:
    product, materialization, result = projected_result(pump=pump)
    assert result.status is CatalogProjectionStatus.READY
    assert result.product_version == product.version
    assert result.materialization_id == materialization.materialization_id
    assert result.schema_fingerprint == materialization.schema_fingerprint
    if pump:
        assert {item.attribute_name for item in result.attributes} >= {"flowRate", "head"}


def test_identity_and_review_warnings_never_block() -> None:
    _, _, result = projected_result(
        manual=True,
        clean=False,
        manufacturer=None,
        model_number=None,
        description=None,
    )
    assert result.status is CatalogProjectionStatus.READY_WITH_WARNINGS
    assert result.blocking_reason_codes == ()
    assert result.warning_reason_codes == (
        CatalogWarningReason.MANUFACTURER_MISSING,
        CatalogWarningReason.MODEL_NUMBER_MISSING,
        CatalogWarningReason.DESCRIPTION_MISSING,
        CatalogWarningReason.OPTIONAL_ATTRIBUTES_UNRESOLVED,
        CatalogWarningReason.HUMAN_OVERRIDE_PRESENT,
    )


def test_unclassified_is_business_blocked_but_category_mismatch_is_technical() -> None:
    materialization = reviewed_materialization()
    unclassified = replace(materialization, category=ProductCategory.UNCLASSIFIED)
    product = catalog_product(unclassified)
    blocked = projection_engine().project(
        job_id=materialization.job_id,
        product=product,
        materialization=unclassified,
        now=NOW,
    )
    assert blocked.status is CatalogProjectionStatus.BLOCKED
    mismatched = replace(product, category=ProductCategory.CENTRIFUGAL_PUMP)
    with pytest.raises(CatalogProjectionCategoryMismatchError):
        projection_engine().project(
            job_id=materialization.job_id,
            product=mismatched,
            materialization=materialization,
            now=NOW,
        )


def test_projection_is_snapshot_and_stably_sorts_shuffled_attributes() -> None:
    materialization = reviewed_materialization()
    shuffled = SimpleNamespace(
        **{field.name: getattr(materialization, field.name) for field in fields(materialization)},
    )
    shuffled.attributes = tuple(reversed(materialization.attributes))
    product = catalog_product(materialization)
    result = projection_engine().project(
        job_id=materialization.job_id,
        product=product,
        materialization=shuffled,
        now=NOW,
    )
    changed_product = replace(product, name="Changed Product", version=4)
    assert result.product_name != changed_product.name and result.product_version == 3
    assert [item.display_order for item in result.attributes] == sorted(
        item.display_order for item in result.attributes
    )
