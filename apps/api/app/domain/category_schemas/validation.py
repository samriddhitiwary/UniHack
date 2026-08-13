"""Safe normalization and bounded schema-validation helpers."""

import re

from app.core.exceptions import CategoryAttributeSchemaValidationError

CANONICAL_NAME_PATTERN = re.compile(r"^[a-z][A-Za-z0-9]*$")
MAX_ATTRIBUTES = 100
MAX_ALIASES_PER_ATTRIBUTE = 30
MAX_ALIAS_LENGTH = 100
MAX_EXAMPLES_PER_ATTRIBUTE = 10
MAX_EXAMPLE_LENGTH = 100


def normalize_alias(value: str) -> str:
    """Normalize separators and case for comparison without rewriting stored aliases."""
    if not isinstance(value, str):
        raise CategoryAttributeSchemaValidationError("alias must be a string")
    normalized = re.sub(r"[_\-]+", " ", value.strip().lower())
    normalized = re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE)
    normalized = " ".join(normalized.split())
    if not normalized:
        raise CategoryAttributeSchemaValidationError("alias must be nonempty")
    return normalized


def bounded_text(value: str, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise CategoryAttributeSchemaValidationError(f"{field} must be a string")
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise CategoryAttributeSchemaValidationError(
            f"{field} must be nonempty and contain at most {maximum} characters"
        )
    return normalized
