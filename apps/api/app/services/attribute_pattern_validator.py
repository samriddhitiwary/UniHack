"""Bounded deterministic full-match validation for trusted schema patterns."""

import re

from app.core.exceptions import AttributeValidationSchemaRuleInvalidError
from app.domain.attribute_validation import (
    AttributeValidationIssue,
    ValidationIssueSeverity,
    ValidationIssueType,
)


class AttributePatternValidator:
    def __init__(self, *, max_pattern_characters: int = 500) -> None:
        if max_pattern_characters < 1:
            raise ValueError("pattern limit must be positive")
        self._max_pattern_characters = max_pattern_characters

    def validate(self, value: str, pattern: str | None) -> tuple[AttributeValidationIssue, ...]:
        if pattern is None:
            return ()
        if len(pattern) > self._max_pattern_characters:
            raise AttributeValidationSchemaRuleInvalidError()
        try:
            compiled = re.compile(pattern)
        except re.error as exc:
            raise AttributeValidationSchemaRuleInvalidError() from exc
        if compiled.fullmatch(value) is None:
            return (
                AttributeValidationIssue.create(
                    ValidationIssueType.PATTERN_VIOLATION,
                    ValidationIssueSeverity.ERROR,
                    "PATTERN_MISMATCH",
                    expected=pattern,
                    actual=value,
                ),
            )
        return ()
