"""Schema-compatible normalized-unit validation without conversion or inference."""

from app.domain.attribute_normalization import NormalizationStatus, NormalizedAttributeCandidate
from app.domain.attribute_validation import (
    AttributeValidationIssue,
    ValidationIssueSeverity,
    ValidationIssueType,
)
from app.domain.category_schemas import AttributeDefinition


class AttributeUnitValidator:
    def validate(
        self, candidate: NormalizedAttributeCandidate, definition: AttributeDefinition
    ) -> tuple[AttributeValidationIssue, ...]:
        if candidate.normalization_status is NormalizationStatus.UNIT_MISSING:
            return (
                AttributeValidationIssue.create(
                    ValidationIssueType.UNIT_MISSING,
                    ValidationIssueSeverity.WARNING,
                    "UNIT_MISSING",
                    expected="one configured canonical unit",
                    actual=None,
                ),
            )
        if candidate.normalization_status is NormalizationStatus.UNSUPPORTED_UNIT:
            return (
                AttributeValidationIssue.create(
                    ValidationIssueType.UNIT_UNSUPPORTED,
                    ValidationIssueSeverity.ERROR,
                    "UNIT_UNSUPPORTED",
                    expected="one configured canonical unit",
                    actual=candidate.raw_unit or candidate.normalized_unit,
                ),
            )
        if definition.allowed_units:
            allowed = {unit.canonical for unit in definition.allowed_units}
            if candidate.normalized_unit not in allowed:
                issue_type = (
                    ValidationIssueType.UNIT_MISSING
                    if candidate.normalized_unit is None
                    else ValidationIssueType.UNIT_UNSUPPORTED
                )
                severity = (
                    ValidationIssueSeverity.WARNING
                    if candidate.normalized_unit is None
                    else ValidationIssueSeverity.ERROR
                )
                return (
                    AttributeValidationIssue.create(
                        issue_type,
                        severity,
                        issue_type.value,
                        expected="|".join(sorted(allowed)),
                        actual=candidate.normalized_unit,
                    ),
                )
        return ()
