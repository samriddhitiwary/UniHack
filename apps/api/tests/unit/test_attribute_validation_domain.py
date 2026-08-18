from dataclasses import FrozenInstanceError, replace
from uuid import uuid4

import pytest

from app.domain.attribute_validation import (
    AttributeValidationIssue,
    ValidationIssueSeverity,
    ValidationIssueType,
)
from app.schemas.attribute_validation import AttributeValidationResultRecord
from app.services.attribute_validation_engine import AttributeValidationEngine
from tests.fixtures.attribute_normalization import NOW
from tests.unit.test_attribute_validation_engine import normalized


def validation_result():
    schema, normalization = normalized(("ratedPower", "5.5", None))
    return AttributeValidationEngine().validate(
        job_id=uuid4(), normalization_result=normalization, schema=schema, now=NOW
    )


def test_models_are_immutable_counts_coherent_and_lineage_exact() -> None:
    result = validation_result()
    assessment = result.assessments[0]
    assert result.normalization_id and result.extraction_id and result.classification_id
    assert (
        assessment.normalized_candidate_id
        and assessment.source_candidate_id
        and assessment.source_id
    )
    assert result.created_at == assessment.created_at == NOW
    with pytest.raises(FrozenInstanceError):
        result.status = result.status  # type: ignore[misc]
    with pytest.raises(ValueError, match="candidate counts"):
        replace(result, valid_count=99)
    with pytest.raises(ValueError, match="issue count"):
        replace(assessment, issue_count=9)


def test_issue_bounds_severity_and_camel_case_serialization() -> None:
    issue = AttributeValidationIssue.create(
        ValidationIssueType.UNIT_MISSING,
        ValidationIssueSeverity.WARNING,
        "UNIT_MISSING",
        expected="canonical unit",
    )
    assert issue.severity is ValidationIssueSeverity.WARNING
    with pytest.raises(ValueError, match="bounded"):
        replace(issue, message_code="x" * 101)
    payload = AttributeValidationResultRecord.model_validate(validation_result()).model_dump(
        mode="json", by_alias=True
    )
    assert payload["validWithWarningsCount"] == 1
    assert payload["assessments"][0]["normalizedCandidateId"]
    assert "selectedCandidateId" not in payload["assessments"][0]
