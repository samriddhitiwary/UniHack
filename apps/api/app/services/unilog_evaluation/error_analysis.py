"""Deterministic field-issue ranking and metric-derived recommendations."""

from collections import Counter

from app.domain.unilog_challenge import FieldPopulationStrategy
from app.domain.unilog_evaluation import (
    EvaluationMatchStatus,
    FieldIssueType,
    UnilogAttributeMetrics,
    UnilogFieldEvaluation,
    UnilogFieldGroup,
    UnilogFieldProblem,
    UnilogImprovementRecommendation,
    UnilogReviewMetrics,
)
from app.services.unilog_challenge.field_strategy import UnilogFieldPopulationStrategy


def analyze_field_errors(
    comparisons: tuple[UnilogFieldEvaluation, ...],
    attributes: UnilogAttributeMetrics,
    review: UnilogReviewMetrics,
) -> tuple[tuple[UnilogFieldProblem, ...], tuple[UnilogImprovementRecommendation, ...]]:
    counts: Counter[tuple[str, FieldIssueType]] = Counter()
    groups: dict[str, UnilogFieldGroup] = {}
    for item in comparisons:
        issue = _issue(item.status)
        if issue is None:
            continue
        counts[(item.field_name, issue)] += 1
        groups[item.field_name] = item.group
    registry = UnilogFieldPopulationStrategy()
    problems = []
    for (field, issue), count in counts.items():
        strategy = registry.for_field(field).strategy
        supported = strategy not in (
            FieldPopulationStrategy.EXTERNAL_ONLY,
            FieldPopulationStrategy.UNSUPPORTED,
        )
        importance = (
            3
            if field in _HIGH_PRIORITY
            or groups[field]
            in (
                UnilogFieldGroup.IDENTITY,
                UnilogFieldGroup.CLASSIFICATION,
                UnilogFieldGroup.DESCRIPTION,
            )
            else 2
            if groups[field] is UnilogFieldGroup.ATTRIBUTE
            else 1
        )
        fixability = 3 if supported and issue is not FieldIssueType.NORMALIZED_ONLY else 1
        problems.append(
            UnilogFieldProblem(
                field_name=field,
                group=groups[field],
                issue_type=issue,
                affected_labelled_rows=count,
                priority_score=count * importance * fixability,
                supported=supported,
            )
        )
    ordered = tuple(
        sorted(
            problems,
            key=lambda item: (-item.priority_score, item.field_name, item.issue_type),
        )
    )
    return ordered, _recommendations(ordered, attributes, review)


_HIGH_PRIORITY = frozenset(
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


def _issue(status: EvaluationMatchStatus) -> FieldIssueType | None:
    return {
        EvaluationMatchStatus.MISMATCH: FieldIssueType.MISMATCH,
        EvaluationMatchStatus.EXPECTED_POPULATED_ACTUAL_BLANK: FieldIssueType.MISSING_EXPECTED,
        EvaluationMatchStatus.EXPECTED_BLANK_ACTUAL_POPULATED: (
            FieldIssueType.UNEXPECTED_POPULATED
        ),
        EvaluationMatchStatus.NORMALIZED_MATCH: FieldIssueType.NORMALIZED_ONLY,
    }.get(status)


def _recommendations(
    problems: tuple[UnilogFieldProblem, ...],
    attributes: UnilogAttributeMetrics,
    review: UnilogReviewMetrics,
) -> tuple[UnilogImprovementRecommendation, ...]:
    by_field: Counter[str] = Counter()
    for item in problems:
        by_field[item.field_name] += item.affected_labelled_rows
    recommendations: list[UnilogImprovementRecommendation] = []
    manufacturer_count = by_field["MANUFACTURER_NAME"] + by_field["BRAND_NAME"]
    if manufacturer_count:
        recommendations.append(
            UnilogImprovementRecommendation(
                code="IMPROVE_MANUFACTURER_BRAND_EVIDENCE",
                title="Improve manufacturer and brand resolution",
                description=(
                    "Supplier names and product-brand evidence need a verified manufacturer source."
                ),
                priority_score=manufacturer_count * 9,
            )
        )
    if by_field["Classpath"]:
        recommendations.append(
            UnilogImprovementRecommendation(
                code="EXPAND_OFFICIAL_CLASSIFICATION_COVERAGE",
                title="Expand official classification coverage",
                description=(
                    "Explicit product types need more verified mappings to official classpaths."
                ),
                priority_score=by_field["Classpath"] * 9,
            )
        )
    if attributes.recall_bp is None or attributes.recall_bp < 5_000:
        recommendations.append(
            UnilogImprovementRecommendation(
                code="IMPROVE_ATTRIBUTE_RECALL",
                title="Improve supported attribute extraction",
                description=(
                    "Recover more labelled values while retaining semantic labels and exact units."
                ),
                priority_score=max(1, attributes.expected_attribute_count) * 2,
            )
        )
    if review.review_required_rate_bp >= 9_000:
        recommendations.append(
            UnilogImprovementRecommendation(
                code="REDUCE_REVIEW_AMBIGUITY",
                title="Reduce evidence ambiguity before auto-approval",
                description=(
                    "Prioritize the largest review-reason groups without lowering confidence gates."
                ),
                priority_score=review.review_required_count,
            )
        )
    if any(item.field_name == "MOBILE_DESC" for item in problems):
        recommendations.append(
            UnilogImprovementRecommendation(
                code="IMPROVE_GROUNDED_MOBILE_DESCRIPTIONS",
                title="Improve grounded mobile descriptions",
                description=(
                    "Add verified facts before targeting the preferred 60-80 character range."
                ),
                priority_score=by_field["MOBILE_DESC"] * 3,
            )
        )
    return tuple(sorted(recommendations, key=lambda item: (-item.priority_score, item.code))[:5])
