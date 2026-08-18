"""Immutable candidate assessments, attribute summaries, and validation results."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.attribute_extraction import AttributeExtractionEvidenceType
from app.domain.attribute_validation.enums import (
    AttributeValidationResultStatus,
    CandidateValidationStatus,
    ValidationIssueSeverity,
    ValidationIssueType,
)
from app.domain.category_schemas import AttributeDataType
from app.domain.products import ProductCategory


def _bounded(value: str | None, name: str, limit: int = 10_000) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ValueError(f"{name} must be nonempty and bounded")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class AttributeValidationIssue:
    issue_id: str
    issue_type: ValidationIssueType
    severity: ValidationIssueSeverity
    message_code: str
    expected: str | None = None
    actual: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "issue_id", _bounded(self.issue_id, "issue_id", 100))
        object.__setattr__(self, "message_code", _bounded(self.message_code, "message_code", 100))
        object.__setattr__(self, "expected", _bounded(self.expected, "expected"))
        object.__setattr__(self, "actual", _bounded(self.actual, "actual"))
        if not isinstance(self.issue_type, ValidationIssueType) or not isinstance(
            self.severity, ValidationIssueSeverity
        ):
            raise ValueError("validation issue type or severity is invalid")

    @classmethod
    def create(
        cls,
        issue_type: ValidationIssueType,
        severity: ValidationIssueSeverity,
        message_code: str,
        *,
        expected: str | None = None,
        actual: str | None = None,
    ) -> "AttributeValidationIssue":
        return cls(
            issue_id=str(uuid4()),
            issue_type=issue_type,
            severity=severity,
            message_code=message_code,
            expected=expected,
            actual=actual,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateValidationAssessment:
    assessment_id: UUID
    normalized_candidate_id: str
    source_candidate_id: str
    attribute_name: str
    attribute_display_name: str
    data_type: AttributeDataType
    status: CandidateValidationStatus
    normalized_value: str | None
    normalized_unit: str | None
    issue_count: int
    error_count: int
    warning_count: int
    issues: tuple[AttributeValidationIssue, ...]
    source_id: UUID
    evidence_type: AttributeExtractionEvidenceType
    evidence_location: str
    created_at: datetime

    def __post_init__(self) -> None:
        for name in (
            "normalized_candidate_id",
            "source_candidate_id",
            "attribute_name",
            "attribute_display_name",
            "evidence_location",
        ):
            _bounded(getattr(self, name), name, 1_000)
        if self.issue_count != len(self.issues):
            raise ValueError("assessment issue count is inconsistent")
        if self.error_count != sum(
            i.severity is ValidationIssueSeverity.ERROR for i in self.issues
        ):
            raise ValueError("assessment error count is inconsistent")
        if self.warning_count != sum(
            i.severity is ValidationIssueSeverity.WARNING for i in self.issues
        ):
            raise ValueError("assessment warning count is inconsistent")
        expected = candidate_status(
            self.issues, self.status is CandidateValidationStatus.NOT_VALIDATABLE
        )
        if self.status is not expected:
            raise ValueError("candidate validation status is inconsistent")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class AttributeValidationSummary:
    attribute_name: str
    candidate_count: int
    valid_candidate_count: int
    valid_with_warnings_candidate_count: int
    invalid_candidate_count: int
    not_validatable_count: int
    issue_count: int

    def __post_init__(self) -> None:
        _bounded(self.attribute_name, "attribute_name", 100)
        if (
            self.candidate_count
            != (
                self.valid_candidate_count
                + self.valid_with_warnings_candidate_count
                + self.invalid_candidate_count
                + self.not_validatable_count
            )
            or min(self.candidate_count, self.issue_count) < 0
        ):
            raise ValueError("attribute validation summary counts are inconsistent")


@dataclass(frozen=True, slots=True, kw_only=True)
class AttributeValidationResult:
    validation_id: UUID
    job_id: UUID
    product_id: UUID
    normalization_id: UUID
    extraction_id: UUID
    classification_id: UUID
    category: ProductCategory
    schema_version: int
    schema_fingerprint: str
    status: AttributeValidationResultStatus
    candidate_count: int
    valid_count: int
    valid_with_warnings_count: int
    invalid_count: int
    not_validatable_count: int
    issue_count: int
    error_count: int
    warning_count: int
    attribute_summary_count: int
    assessments: tuple[CandidateValidationAssessment, ...]
    attribute_summaries: tuple[AttributeValidationSummary, ...]
    warning_codes: tuple[str, ...]
    engine: str
    engine_version: str
    created_at: datetime

    def __post_init__(self) -> None:
        counts = {
            CandidateValidationStatus.VALID: self.valid_count,
            CandidateValidationStatus.VALID_WITH_WARNINGS: self.valid_with_warnings_count,
            CandidateValidationStatus.INVALID: self.invalid_count,
            CandidateValidationStatus.NOT_VALIDATABLE: self.not_validatable_count,
        }
        if self.candidate_count != len(self.assessments) or any(
            value != sum(a.status is status for a in self.assessments)
            for status, value in counts.items()
        ):
            raise ValueError("validation candidate counts are inconsistent")
        if (
            self.issue_count != sum(a.issue_count for a in self.assessments)
            or self.error_count != sum(a.error_count for a in self.assessments)
            or self.warning_count != sum(a.warning_count for a in self.assessments)
        ):
            raise ValueError("validation issue counts are inconsistent")
        if self.attribute_summary_count != len(self.attribute_summaries):
            raise ValueError("attribute summary count is inconsistent")
        if self.status is not result_status(self.assessments):
            raise ValueError("validation result status is inconsistent")
        if (
            len(set(self.warning_codes)) != len(self.warning_codes)
            or not self.engine
            or not self.engine_version
        ):
            raise ValueError("validation metadata is invalid")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))

    @classmethod
    def create(
        cls,
        *,
        job_id: UUID,
        product_id: UUID,
        normalization_id: UUID,
        extraction_id: UUID,
        classification_id: UUID,
        category: ProductCategory,
        schema_version: int,
        schema_fingerprint: str,
        assessments: tuple[CandidateValidationAssessment, ...],
        attribute_summaries: tuple[AttributeValidationSummary, ...],
        now: datetime,
    ) -> "AttributeValidationResult":
        return cls(
            validation_id=uuid4(),
            job_id=job_id,
            product_id=product_id,
            normalization_id=normalization_id,
            extraction_id=extraction_id,
            classification_id=classification_id,
            category=category,
            schema_version=schema_version,
            schema_fingerprint=schema_fingerprint,
            status=result_status(assessments),
            candidate_count=len(assessments),
            valid_count=sum(a.status is CandidateValidationStatus.VALID for a in assessments),
            valid_with_warnings_count=sum(
                a.status is CandidateValidationStatus.VALID_WITH_WARNINGS for a in assessments
            ),
            invalid_count=sum(a.status is CandidateValidationStatus.INVALID for a in assessments),
            not_validatable_count=sum(
                a.status is CandidateValidationStatus.NOT_VALIDATABLE for a in assessments
            ),
            issue_count=sum(a.issue_count for a in assessments),
            error_count=sum(a.error_count for a in assessments),
            warning_count=sum(a.warning_count for a in assessments),
            attribute_summary_count=len(attribute_summaries),
            assessments=assessments,
            attribute_summaries=attribute_summaries,
            warning_codes=tuple(
                dict.fromkeys(i.issue_type.value for a in assessments for i in a.issues)
            ),
            engine="deterministic-attribute-validator-v1",
            engine_version="1.0",
            created_at=now,
        )


def candidate_status(
    issues: tuple[AttributeValidationIssue, ...], not_validatable: bool = False
) -> CandidateValidationStatus:
    if not_validatable:
        return CandidateValidationStatus.NOT_VALIDATABLE
    if any(i.severity is ValidationIssueSeverity.ERROR for i in issues):
        return CandidateValidationStatus.INVALID
    if any(i.severity is ValidationIssueSeverity.WARNING for i in issues):
        return CandidateValidationStatus.VALID_WITH_WARNINGS
    return CandidateValidationStatus.VALID


def result_status(
    assessments: tuple[CandidateValidationAssessment, ...],
) -> AttributeValidationResultStatus:
    if not assessments or all(
        a.status is CandidateValidationStatus.NOT_VALIDATABLE for a in assessments
    ):
        return AttributeValidationResultStatus.NO_VALIDATABLE_CANDIDATES
    if any(
        a.status in {CandidateValidationStatus.INVALID, CandidateValidationStatus.NOT_VALIDATABLE}
        for a in assessments
    ):
        return AttributeValidationResultStatus.INVALID_CANDIDATES_FOUND
    if any(a.status is CandidateValidationStatus.VALID_WITH_WARNINGS for a in assessments):
        return AttributeValidationResultStatus.VALID_WITH_WARNINGS
    return AttributeValidationResultStatus.ALL_VALID
