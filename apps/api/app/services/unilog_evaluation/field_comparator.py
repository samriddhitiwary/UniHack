"""Field-aware comparison and immutable delivery-field grouping."""

import re
from collections import Counter
from collections.abc import Iterable

from app.domain.unilog_evaluation import (
    EvaluationMatchStatus,
    UnilogAccuracyMetrics,
    UnilogFieldEvaluation,
    UnilogFieldGroup,
)

_CORE = frozenset(
    {
        "MANUFACTURER_NAME",
        "BRAND_NAME",
        "MANUFACTURER_PART_NUMBER",
        "Classpath",
        "Product Name",
        "MOBILE_DESC",
        "INVOICE_DESC",
        "SHORT_DESC",
        "LONG_DESC1",
    }
)
_IDENTITY = frozenset(
    {
        "PART_NUMBER",
        "SKU - MY_PART_NUMBER",
        "Mfg_Part_Num",
        "Part_Desc",
        "E1_Brand",
        "Unilog_Brand",
        "DIB_Brand",
        "Part_Manuf",
        "MANUFACTURER_NAME",
        "BRAND_NAME",
        "TRADE_NAME",
        "MANUFACTURER_PART_NUMBER",
        "ALTERNATE_PART_NUMBER",
    }
)
_CLASSIFICATION = frozenset({"Dept", "Class", "Fine", "Classpath", "Product Name"})
_DESCRIPTIONS = frozenset(
    {
        "MOBILE_DESC",
        "INVOICE_DESC",
        "SHORT_DESC",
        "LONG_DESC1",
        "RETAIL_DESC",
        "MARKETING_DESCRIPTION",
    }
)
_ATTRIBUTE_OTHER = frozenset({"With", "Standard/Approvals", "Prop 65", "Application", "Includes"})
_COMMERCIAL = frozenset(
    {
        "UPC",
        "EAN",
        "GTIN",
        "UNSPSC",
        "Warranty",
        "List Price",
        "Selling Qty",
        "Selling UOM",
        "Standard Packaging Information",
    }
)
_DIMENSIONS = frozenset(
    {
        "LENGTH",
        "LENGTH_UOM",
        "HEIGHT",
        "HEIGHT_UOM",
        "WIDTH",
        "WIDTH_UOM",
        "WEIGHT",
        "WEIGHT_UOM",
        "VOLUME",
        "VOLUME_UOM",
    }
)
_ASSETS = frozenset(
    {
        "Product Image",
        *(f"Alternate Image {index}" for index in range(1, 5)),
        "Video Link",
        "Video Link 1",
        "Actual Image (Yes/No)",
    }
)
_DOCUMENTS = frozenset(
    {
        "SDS",
        "SDS_1",
        "Warranty Information",
        "Catalog",
        "Specification Sheet",
        "Instruction/Installation Manual",
        "Service Manual",
        "Owners/User Manual",
        "Line Drawing",
        "MTR",
        "RoHS",
        "Full Engineering Drawing",
        "Energy Star Guide",
        "Technical Bulletin",
        "Submittal",
        "Compatibility Chart",
        "Size Chart",
        "Product Label/Insert",
    }
)
_REFERENCES = frozenset({"MFR URL", *(f"Ref URL {index}" for index in range(1, 6))})
_CASE_INSENSITIVE = (
    _CLASSIFICATION
    | (_DESCRIPTIONS - {"INVOICE_DESC"})
    | {
        "MANUFACTURER_NAME",
        "BRAND_NAME",
        "TRADE_NAME",
    }
)


def field_group(field: str) -> UnilogFieldGroup:
    if field in _IDENTITY:
        return UnilogFieldGroup.IDENTITY
    if field in _CLASSIFICATION:
        return UnilogFieldGroup.CLASSIFICATION
    if field in _DESCRIPTIONS:
        return UnilogFieldGroup.DESCRIPTION
    if field.startswith("ITEM_FEATURES_"):
        return UnilogFieldGroup.FEATURE
    if field.startswith("ATTRIBUTE_") or field in _ATTRIBUTE_OTHER:
        return UnilogFieldGroup.ATTRIBUTE
    if field in _COMMERCIAL:
        return UnilogFieldGroup.COMMERCIAL
    if field in _DIMENSIONS:
        return UnilogFieldGroup.DIMENSION
    if field in _ASSETS:
        return UnilogFieldGroup.ASSET
    if field in _DOCUMENTS:
        return UnilogFieldGroup.DOCUMENT
    if field in _REFERENCES:
        return UnilogFieldGroup.REFERENCE
    return UnilogFieldGroup.OTHER


def compare_delivery_field(
    field: str, expected: str | None, actual: str | None
) -> UnilogFieldEvaluation:
    expected = None if expected in (None, "") else str(expected)
    actual = None if actual in (None, "") else str(actual)
    method: str | None = None
    if expected is None and actual is None:
        status = EvaluationMatchStatus.BOTH_BLANK
    elif expected is None:
        status = EvaluationMatchStatus.EXPECTED_BLANK_ACTUAL_POPULATED
    elif actual is None:
        status = EvaluationMatchStatus.EXPECTED_POPULATED_ACTUAL_BLANK
    elif expected == actual:
        status = EvaluationMatchStatus.EXACT_MATCH
    else:
        expected_normalized = _safe_normalize(field, expected)
        actual_normalized = _safe_normalize(field, actual)
        if expected_normalized == actual_normalized:
            status = EvaluationMatchStatus.NORMALIZED_MATCH
            method = (
                "trim-line-endings-collapse-whitespace-casefold"
                if field in _CASE_INSENSITIVE
                else "trim-line-endings-collapse-whitespace"
            )
        else:
            status = EvaluationMatchStatus.MISMATCH
    return UnilogFieldEvaluation(
        field_name=field,
        group=field_group(field),
        expected_value=expected,
        actual_value=actual,
        status=status,
        normalized_method=method,
        core_enrichment_field=(
            field in _CORE or (field.startswith("ATTRIBUTE_") and expected is not None)
        ),
    )


def _safe_normalize(field: str, value: str) -> str:
    normalized = re.sub(r"[\t ]+", " ", value.replace("\r\n", "\n").replace("\r", "\n"))
    normalized = re.sub(r" *\n *", "\n", normalized).strip()
    return normalized.casefold() if field in _CASE_INSENSITIVE else normalized


def accuracy_metrics(
    comparisons: Iterable[UnilogFieldEvaluation],
) -> UnilogAccuracyMetrics:
    counts = Counter(item.status for item in comparisons)
    evaluable = sum(
        counts[status]
        for status in (
            EvaluationMatchStatus.EXACT_MATCH,
            EvaluationMatchStatus.NORMALIZED_MATCH,
            EvaluationMatchStatus.MISMATCH,
            EvaluationMatchStatus.EXPECTED_POPULATED_ACTUAL_BLANK,
        )
    )
    exact = counts[EvaluationMatchStatus.EXACT_MATCH]
    accepted = exact + counts[EvaluationMatchStatus.NORMALIZED_MATCH]
    return UnilogAccuracyMetrics(
        exact_match_count=exact,
        normalized_match_count=counts[EvaluationMatchStatus.NORMALIZED_MATCH],
        mismatch_count=counts[EvaluationMatchStatus.MISMATCH],
        expected_populated_actual_blank_count=counts[
            EvaluationMatchStatus.EXPECTED_POPULATED_ACTUAL_BLANK
        ],
        expected_blank_actual_populated_count=counts[
            EvaluationMatchStatus.EXPECTED_BLANK_ACTUAL_POPULATED
        ],
        both_blank_count=counts[EvaluationMatchStatus.BOTH_BLANK],
        not_evaluated_count=counts[EvaluationMatchStatus.NOT_EVALUATED],
        evaluable_field_count=evaluable,
        exact_match_rate_bp=exact * 10_000 // evaluable if evaluable else 0,
        accepted_match_rate_bp=accepted * 10_000 // evaluable if evaluable else 0,
    )
