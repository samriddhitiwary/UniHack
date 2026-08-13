from dataclasses import FrozenInstanceError, replace
from uuid import uuid4

import pytest

from app.domain.attribute_completeness import percentage_basis_points
from app.services.attribute_completeness_engine import AttributeCompletenessEngine
from tests.fixtures.attribute_normalization import NOW
from tests.unit.test_attribute_completeness_engine import conflict_for


def test_completeness_models_are_immutable_and_lineage_is_exact() -> None:
    schema, conflict = conflict_for(("voltage", "415", "V"))
    result = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(), conflict_result=conflict, schema=schema, now=NOW
    )
    assert result.conflict_detection_id == conflict.conflict_detection_id
    assert result.normalization_id == conflict.normalization_id
    assert result.extraction_id == conflict.extraction_id
    assert result.classification_id == conflict.classification_id
    assert result.created_at == NOW
    with pytest.raises(FrozenInstanceError):
        result.status = result.status  # type: ignore[misc]


def test_completeness_domain_rejects_incoherent_counts_and_percentages() -> None:
    schema, conflict = conflict_for(("voltage", "415", "V"))
    result = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(), conflict_result=conflict, schema=schema, now=NOW
    )
    with pytest.raises(ValueError, match="counts are inconsistent"):
        replace(result, total_missing_count=result.total_missing_count + 1)
    with pytest.raises(ValueError, match="percentages are inconsistent"):
        replace(result, required_available_bp=10_001)
    with pytest.raises(ValueError, match="percentage counts are invalid"):
        percentage_basis_points(2, 1)
