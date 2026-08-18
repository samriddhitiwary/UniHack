from types import SimpleNamespace

import pytest

from app.core.exceptions import CatalogProjectionProductTextLimitExceededError
from app.domain.catalog_projection import CatalogBlockingReason, CatalogWarningReason
from app.domain.products import ProductCategory
from app.services.catalog_product_identity_projector import CatalogProductIdentityProjector
from tests.fixtures.catalog_projection import catalog_product, reviewed_materialization


def test_snapshots_exact_product_identity_and_version_without_inference() -> None:
    materialization = reviewed_materialization()
    product = catalog_product(materialization)
    result = CatalogProductIdentityProjector().project(product)
    assert result.identity.product_id == product.product_id
    assert result.identity.product_version == product.version == 3
    assert result.identity.product_name == product.name
    assert result.blockers == () and result.warnings == ()


def test_missing_optional_identity_fields_are_stable_warnings() -> None:
    materialization = reviewed_materialization()
    product = catalog_product(
        materialization, manufacturer=None, model_number=None, description=None
    )
    result = CatalogProductIdentityProjector().project(product)
    assert result.warnings == (
        CatalogWarningReason.MANUFACTURER_MISSING,
        CatalogWarningReason.MODEL_NUMBER_MISSING,
        CatalogWarningReason.DESCRIPTION_MISSING,
    )


def test_defensive_name_and_unclassified_checks_and_text_limit() -> None:
    materialization = reviewed_materialization()
    product = catalog_product(materialization)
    malformed = SimpleNamespace(
        **{
            field: getattr(product, field)
            for field in (
                "product_id",
                "version",
                "manufacturer",
                "model_number",
                "description",
            )
        },
        name=" ",
        category=ProductCategory.UNCLASSIFIED,
    )
    result = CatalogProductIdentityProjector().project(malformed)
    assert result.blockers == (
        CatalogBlockingReason.PRODUCT_NAME_MISSING,
        CatalogBlockingReason.PRODUCT_CATEGORY_UNCLASSIFIED,
    )
    with pytest.raises(CatalogProjectionProductTextLimitExceededError):
        CatalogProductIdentityProjector(max_text_characters=1).project(product)
