"""Decimal-only type, range, and allowed-value validation."""

from decimal import Decimal, InvalidOperation

from app.domain.attribute_validation import (
    AttributeValidationIssue,
    ValidationIssueSeverity,
    ValidationIssueType,
)
from app.domain.category_schemas import AttributeDataType, AttributeDefinition


class AttributeNumericValidator:
    def validate(
        self, value: str | None, definition: AttributeDefinition
    ) -> tuple[AttributeValidationIssue, ...]:
        if value is None:
            return (_issue(ValidationIssueType.TYPE_INVALID, "VALUE_REQUIRED", actual=None),)
        try:
            number = Decimal(value)
            if not number.is_finite():
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            return (_issue(ValidationIssueType.TYPE_INVALID, "DECIMAL_REQUIRED", actual=value),)
        issues: list[AttributeValidationIssue] = []
        if (
            definition.data_type is AttributeDataType.INTEGER
            and number != number.to_integral_value()
        ):
            issues.append(
                _issue(ValidationIssueType.TYPE_INVALID, "INTEGER_REQUIRED", actual=value)
            )
            return tuple(issues)
        rules = definition.validation_rules
        if rules.min_value is not None and number < Decimal(str(rules.min_value)):
            issues.append(
                _issue(
                    ValidationIssueType.NUMERIC_MIN_VIOLATION,
                    "VALUE_BELOW_MIN",
                    expected=f">={rules.min_value}",
                    actual=value,
                )
            )
        if rules.max_value is not None and number > Decimal(str(rules.max_value)):
            issues.append(
                _issue(
                    ValidationIssueType.NUMERIC_MAX_VIOLATION,
                    "VALUE_ABOVE_MAX",
                    expected=f"<={rules.max_value}",
                    actual=value,
                )
            )
        return tuple(issues)


def _issue(
    issue_type: ValidationIssueType,
    code: str,
    *,
    expected: str | None = None,
    actual: str | None = None,
) -> AttributeValidationIssue:
    return AttributeValidationIssue.create(
        issue_type, ValidationIssueSeverity.ERROR, code, expected=expected, actual=actual
    )
