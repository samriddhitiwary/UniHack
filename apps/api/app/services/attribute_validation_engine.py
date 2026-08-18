"""Deterministic schema-driven candidate validation."""

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.exceptions import (
    AttributeValidationAttributeLimitExceededError,
    AttributeValidationCandidateLimitExceededError,
    AttributeValidationIssueLimitExceededError,
    AttributeValidationSchemaMismatchError,
    AttributeValidationUnknownAttributeError,
    AttributeValidationValueLimitExceededError,
)
from app.domain.attribute_normalization import (
    AttributeNormalizationResult,
    NormalizationStatus,
    NormalizedAttributeCandidate,
)
from app.domain.attribute_validation import (
    AttributeValidationIssue,
    AttributeValidationResult,
    AttributeValidationSummary,
    CandidateValidationAssessment,
    CandidateValidationStatus,
    ValidationIssueSeverity,
    ValidationIssueType,
    candidate_status,
)
from app.domain.category_schemas import (
    AttributeDataType,
    AttributeDefinition,
    CategoryAttributeSchema,
)
from app.services.attribute_numeric_validator import AttributeNumericValidator
from app.services.attribute_pattern_validator import AttributePatternValidator
from app.services.attribute_unit_validator import AttributeUnitValidator

logger = logging.getLogger(__name__)


class AttributeValidationEngine:
    def __init__(
        self,
        *,
        max_candidates: int = 5_000,
        max_attributes: int = 100,
        max_value_characters: int = 10_000,
        max_pattern_characters: int = 500,
        max_issues_per_candidate: int = 20,
        max_total_issues: int = 10_000,
    ) -> None:
        limits = (
            max_candidates,
            max_attributes,
            max_value_characters,
            max_pattern_characters,
            max_issues_per_candidate,
            max_total_issues,
        )
        if any(limit < 1 for limit in limits):
            raise ValueError("attribute validation limits must be positive")
        self._max_candidates, self._max_attributes = max_candidates, max_attributes
        self._max_value_characters = max_value_characters
        self._max_issues_per_candidate, self._max_total_issues = (
            max_issues_per_candidate,
            max_total_issues,
        )
        self._numeric = AttributeNumericValidator()
        self._pattern = AttributePatternValidator(max_pattern_characters=max_pattern_characters)
        self._unit = AttributeUnitValidator()

    def validate(
        self,
        *,
        job_id: UUID,
        normalization_result: AttributeNormalizationResult,
        schema: CategoryAttributeSchema,
        now: datetime | None = None,
    ) -> AttributeValidationResult:
        if (
            schema.category != normalization_result.category
            or schema.version != normalization_result.schema_version
            or schema.schema_fingerprint != normalization_result.schema_fingerprint
        ):
            raise AttributeValidationSchemaMismatchError()
        if len(normalization_result.candidates) > self._max_candidates:
            raise AttributeValidationCandidateLimitExceededError()
        if len(schema.attributes) > self._max_attributes:
            raise AttributeValidationAttributeLimitExceededError()
        definitions = {item.canonical_name: item for item in schema.attributes}
        timestamp = (now or datetime.now(UTC)).astimezone(UTC)
        assessments: list[CandidateValidationAssessment] = []
        for candidate in normalization_result.candidates:
            definition = definitions.get(candidate.attribute_name)
            if definition is None:
                raise AttributeValidationUnknownAttributeError()
            assessment = self._assess(candidate, definition, timestamp)
            assessments.append(assessment)
            if sum(item.issue_count for item in assessments) > self._max_total_issues:
                raise AttributeValidationIssueLimitExceededError()
            logger.info(
                "event=attribute_validation.candidate_%s attribute_name=%s "
                "candidate_id=%s status=%s issue_count=%s",
                assessment.status.value.lower(),
                assessment.attribute_name,
                assessment.normalized_candidate_id,
                assessment.status.value,
                assessment.issue_count,
            )
        summaries = self._summaries(tuple(assessments), schema)
        return AttributeValidationResult.create(
            job_id=job_id,
            product_id=normalization_result.product_id,
            normalization_id=normalization_result.normalization_id,
            extraction_id=normalization_result.extraction_id,
            classification_id=normalization_result.classification_id,
            category=normalization_result.category,
            schema_version=normalization_result.schema_version,
            schema_fingerprint=normalization_result.schema_fingerprint,
            assessments=tuple(assessments),
            attribute_summaries=summaries,
            now=timestamp,
        )

    def _assess(
        self,
        candidate: NormalizedAttributeCandidate,
        definition: AttributeDefinition,
        timestamp: datetime,
    ) -> CandidateValidationAssessment:
        for value in (candidate.normalized_value, candidate.normalized_unit):
            if value is not None and len(value) > self._max_value_characters:
                raise AttributeValidationValueLimitExceededError()
        issues: tuple[AttributeValidationIssue, ...]
        if candidate.normalization_status is NormalizationStatus.INVALID_VALUE:
            issues = (
                AttributeValidationIssue.create(
                    ValidationIssueType.NORMALIZATION_INVALID,
                    ValidationIssueSeverity.ERROR,
                    "NORMALIZATION_INVALID",
                ),
            )
            status = CandidateValidationStatus.NOT_VALIDATABLE
        else:
            issues = (
                *self._type_and_rules(candidate.normalized_value, definition),
                *self._unit.validate(candidate, definition),
            )
            status = candidate_status(issues)
        if len(issues) > self._max_issues_per_candidate:
            raise AttributeValidationIssueLimitExceededError()
        return CandidateValidationAssessment(
            assessment_id=uuid4(),
            normalized_candidate_id=candidate.normalized_candidate_id,
            source_candidate_id=candidate.source_candidate_id,
            attribute_name=candidate.attribute_name,
            attribute_display_name=candidate.attribute_display_name,
            data_type=definition.data_type,
            status=status,
            normalized_value=candidate.normalized_value,
            normalized_unit=candidate.normalized_unit,
            issue_count=len(issues),
            error_count=sum(i.severity is ValidationIssueSeverity.ERROR for i in issues),
            warning_count=sum(i.severity is ValidationIssueSeverity.WARNING for i in issues),
            issues=issues,
            source_id=candidate.source_id,
            evidence_type=candidate.evidence_type,
            evidence_location=candidate.evidence_location,
            created_at=timestamp,
        )

    def _type_and_rules(
        self, value: str | None, definition: AttributeDefinition
    ) -> tuple[AttributeValidationIssue, ...]:
        if definition.data_type in {AttributeDataType.NUMBER, AttributeDataType.INTEGER}:
            issues = list(self._numeric.validate(value, definition))
        elif value is None or not value.strip():
            issues = [
                AttributeValidationIssue.create(
                    ValidationIssueType.TYPE_INVALID,
                    ValidationIssueSeverity.ERROR,
                    "NONEMPTY_VALUE_REQUIRED",
                    actual=value,
                )
            ]
        elif definition.data_type is AttributeDataType.BOOLEAN and value not in {"true", "false"}:
            issues = [
                AttributeValidationIssue.create(
                    ValidationIssueType.TYPE_INVALID,
                    ValidationIssueSeverity.ERROR,
                    "CANONICAL_BOOLEAN_REQUIRED",
                    expected="true|false",
                    actual=value,
                )
            ]
        else:
            issues = []
        if (
            value is not None
            and definition.validation_rules.allowed_values
            and value not in definition.validation_rules.allowed_values
        ):
            issues.append(
                AttributeValidationIssue.create(
                    ValidationIssueType.ALLOWED_VALUE_VIOLATION,
                    ValidationIssueSeverity.ERROR,
                    "VALUE_NOT_ALLOWED",
                    expected="configured allowed values",
                    actual=value,
                )
            )
        if value is not None:
            issues.extend(self._pattern.validate(value, definition.validation_rules.pattern))
        return tuple(issues)

    @staticmethod
    def _summaries(
        assessments: tuple[CandidateValidationAssessment, ...], schema: CategoryAttributeSchema
    ) -> tuple[AttributeValidationSummary, ...]:
        output = []
        for definition in sorted(schema.attributes, key=lambda item: item.display_order):
            items = tuple(a for a in assessments if a.attribute_name == definition.canonical_name)
            if not items:
                continue
            output.append(
                AttributeValidationSummary(
                    attribute_name=definition.canonical_name,
                    candidate_count=len(items),
                    valid_candidate_count=sum(
                        a.status is CandidateValidationStatus.VALID for a in items
                    ),
                    valid_with_warnings_candidate_count=sum(
                        a.status is CandidateValidationStatus.VALID_WITH_WARNINGS for a in items
                    ),
                    invalid_candidate_count=sum(
                        a.status is CandidateValidationStatus.INVALID for a in items
                    ),
                    not_validatable_count=sum(
                        a.status is CandidateValidationStatus.NOT_VALIDATABLE for a in items
                    ),
                    issue_count=sum(a.issue_count for a in items),
                )
            )
        return tuple(output)
