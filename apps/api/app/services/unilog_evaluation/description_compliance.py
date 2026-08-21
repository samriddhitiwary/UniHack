"""Description-format, grounding, numeric, and duplicate-token analytics."""

import re
from collections import defaultdict
from itertools import pairwise

from app.domain.unilog_challenge import UnilogBatchEnrichmentResult, UnilogDescriptionResult
from app.domain.unilog_evaluation import (
    UnilogDescriptionComplianceMetrics,
    UnilogDescriptionFieldMetrics,
)

_FIELDS = (
    "INVOICE_DESC",
    "MOBILE_DESC",
    "SHORT_DESC",
    "LONG_DESC1",
    "RETAIL_DESC",
    "MARKETING_DESCRIPTION",
)


def evaluate_description_compliance(
    batch: UnilogBatchEnrichmentResult,
) -> UnilogDescriptionComplianceMetrics:
    completed = tuple(item.enrichment for item in batch.rows if item.enrichment is not None)
    row_count = len(batch.rows)
    by_field: dict[str, list[UnilogDescriptionResult]] = defaultdict(list)
    for enrichment in completed:
        for description in enrichment.descriptions:
            by_field[description.field_name].append(description)
    field_metrics = tuple(_field_metrics(field, by_field[field], row_count) for field in _FIELDS)
    invoice = [item for item in by_field["INVOICE_DESC"] if item.value]
    mobile = [item for item in by_field["MOBILE_DESC"] if item.value]
    generated = [item for field in _FIELDS for item in by_field[field] if item.value is not None]
    grounded = sum(_grounded(item) for item in generated)
    traceable = sum(_numeric_traceable(item) for item in generated)
    violations = sum(
        issue.startswith("INVALID_")
        for field in _FIELDS
        for item in by_field[field]
        for issue in item.validation_issues
    )
    return UnilogDescriptionComplianceMetrics(
        invoice_populated_count=len(invoice),
        invoice_uppercase_compliance_bp=_rate(
            sum((item.value or "") == (item.value or "").upper() for item in invoice),
            len(invoice),
        ),
        invoice_max_40_compliance_bp=_rate(
            sum(len(item.value or "") <= 40 for item in invoice), len(invoice)
        ),
        invoice_non_empty_rate_bp=_rate(len(invoice), row_count),
        mobile_populated_count=len(mobile),
        mobile_preferred_length_rate_bp=_rate(
            sum(60 <= len(item.value or "") <= 80 for item in mobile), len(mobile)
        ),
        mobile_under_60_rate_bp=_rate(
            sum(len(item.value or "") < 60 for item in mobile), len(mobile)
        ),
        mobile_over_80_rate_bp=_rate(
            sum(len(item.value or "") > 80 for item in mobile), len(mobile)
        ),
        grounding_compliance_bp=_rate(grounded, len(generated)),
        numeric_traceability_bp=_rate(traceable, len(generated)),
        unsupported_fact_violation_count=violations,
        fields=field_metrics,
    )


def _field_metrics(
    field: str, items: list[UnilogDescriptionResult], row_count: int
) -> UnilogDescriptionFieldMetrics:
    populated = [item for item in items if item.value]
    return UnilogDescriptionFieldMetrics(
        field_name=field,
        populated_count=len(populated),
        non_empty_rate_bp=_rate(len(populated), row_count),
        grounding_compliance_bp=_rate(sum(_grounded(item) for item in populated), len(populated)),
        numeric_traceability_bp=_rate(
            sum(_numeric_traceable(item) for item in populated), len(populated)
        ),
        duplicate_token_warning_count=sum(
            _has_adjacent_duplicate(item.value or "") for item in populated
        ),
    )


def _grounded(item: UnilogDescriptionResult) -> bool:
    return bool(item.fact_ids) and not any(
        issue.startswith("INVALID_") for issue in item.validation_issues
    )


def _numeric_traceable(item: UnilogDescriptionResult) -> bool:
    return "INVALID_UNSUPPORTED_NUMBER" not in item.validation_issues


def _has_adjacent_duplicate(value: str) -> bool:
    tokens = re.findall(r"[A-Za-z0-9®™-]+", value.casefold())
    return any(left == right for left, right in pairwise(tokens))


def _rate(numerator: int, denominator: int) -> int:
    return numerator * 10_000 // denominator if denominator else 0
