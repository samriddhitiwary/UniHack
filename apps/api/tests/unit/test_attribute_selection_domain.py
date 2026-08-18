from dataclasses import FrozenInstanceError, replace

import pytest

from app.domain.attribute_selection import AttributeSelectionStatus
from app.schemas.attribute_selection import AttributeSelectionResultRecord
from tests.unit.test_attribute_selection_engine import attr, pipeline


def test_selection_models_are_immutable_and_proposals_are_auto_only() -> None:
    *_, result = pipeline(("ratedPower", "5.5", "kW"), ("ratedPower", "5.5", "kW"))
    selected = attr(result, "ratedPower")
    with pytest.raises(FrozenInstanceError):
        result.overall_status = result.overall_status  # type: ignore[misc]
    with pytest.raises(ValueError, match="only auto-selected"):
        replace(
            selected,
            selection_status=AttributeSelectionStatus.REVIEW_REQUIRED,
            review_required=True,
        )
    with pytest.raises(ValueError, match="confidence"):
        replace(selected, selection_confidence_bp=10_001)
    with pytest.raises(ValueError, match="status counts"):
        replace(result, auto_selected_count=99)


def test_selection_schema_serializes_lineage_and_null_review_proposals() -> None:
    *_, result = pipeline(("voltage", "415", "V"), ("voltage", "440", "V"))
    payload = AttributeSelectionResultRecord.model_validate(result).model_dump(
        mode="json", by_alias=True
    )
    voltage = next(item for item in payload["attributes"] if item["attributeName"] == "voltage")
    assert voltage["proposedValue"] is None and len(voltage["reviewCandidateIds"]) == 2
    assert payload["conflictDetectionId"] and payload["validationId"] and payload["completenessId"]
    assert "approvedValue" not in voltage
