from dataclasses import fields
from types import SimpleNamespace

import pytest

from app.core.exceptions import CatalogProjectionRequiredAttributesIncompleteError
from app.domain.catalog_projection import CatalogWarningReason
from app.domain.reviewed_attributes import FinalAttributeOrigin
from app.services.catalog_reviewed_attribute_projector import CatalogReviewedAttributeProjector
from tests.fixtures.catalog_projection import reviewed_materialization


def test_projects_only_compact_reviewed_lineage_in_display_order() -> None:
    materialization = reviewed_materialization()
    result = CatalogReviewedAttributeProjector().project(materialization)
    assert [item.display_order for item in result.attributes] == sorted(
        item.display_order for item in result.attributes
    )
    assert all(item.review_decision_id for item in result.attributes)
    assert not hasattr(result.attributes[0], "manual_raw_value")
    assert not hasattr(result.attributes[0], "source_candidate_id")


def test_preserves_manual_validation_and_optional_warnings() -> None:
    manual = CatalogReviewedAttributeProjector().project(
        reviewed_materialization(manual=True, clean=False)
    )
    assert CatalogWarningReason.HUMAN_OVERRIDE_PRESENT in manual.warnings
    voltage = next(item for item in manual.attributes if item.attribute_name == "voltage")
    assert voltage.origin is FinalAttributeOrigin.HUMAN_OVERRIDE and voltage.candidate_id is None
    warning = CatalogReviewedAttributeProjector().project(
        reviewed_materialization(warning=True, clean=False)
    )
    assert CatalogWarningReason.VALIDATION_WARNING_PRESENT in warning.warnings
    assert CatalogWarningReason.OPTIONAL_ATTRIBUTES_UNRESOLVED in warning.warnings


def test_rejects_malformed_required_counts() -> None:
    materialization = reviewed_materialization()
    malformed = SimpleNamespace(
        **{field.name: getattr(materialization, field.name) for field in fields(materialization)},
    )
    malformed.materialized_required_count -= 1
    with pytest.raises(CatalogProjectionRequiredAttributesIncompleteError):
        CatalogReviewedAttributeProjector().project(malformed)
