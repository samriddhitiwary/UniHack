from dataclasses import replace
from uuid import uuid4

import pytest

from app.core.exceptions import (
    AttributeValidationAttributeLimitExceededError,
    AttributeValidationCandidateLimitExceededError,
    AttributeValidationIssueLimitExceededError,
    AttributeValidationSchemaRuleInvalidError,
    AttributeValidationUnknownAttributeError,
    AttributeValidationValueLimitExceededError,
)
from app.domain.attribute_normalization import AttributeNormalizationResult, NormalizationStatus
from app.domain.attribute_validation import (
    AttributeValidationResultStatus,
    CandidateValidationStatus,
    ValidationIssueSeverity,
    ValidationIssueType,
)
from app.domain.category_schemas import AttributeValidationRules, CategoryAttributeSchema
from app.domain.category_schemas.builtins import induction_motor_schema_v1
from app.services.attribute_normalization_engine import AttributeNormalizationEngine
from app.services.attribute_validation_engine import AttributeValidationEngine
from tests.fixtures.attribute_normalization import NOW, candidate, extraction


def normalized(*items):
    schema = induction_motor_schema_v1()
    sources = tuple(
        candidate(schema, name, value, unit, index=index)
        for index, (name, value, unit) in enumerate(items, 1)
    )
    return schema, AttributeNormalizationEngine().normalize(
        job_id=uuid4(), extraction_result=extraction(schema, sources), schema=schema, now=NOW
    )


def validate(*items):
    schema, result = normalized(*items)
    return AttributeValidationEngine().validate(
        job_id=uuid4(), normalization_result=result, schema=schema, now=NOW
    )


def test_valid_motor_candidates_and_valid_conflicting_values_are_preserved() -> None:
    result = validate(
        ("ratedPower", "5.5", "kW"),
        ("voltage", "415", "V"),
        ("voltage", "440", "V"),
        ("frequency", "50", "Hz"),
        ("speedRpm", "1440", "rpm"),
        ("phase", "3", None),
    )
    assert result.status is AttributeValidationResultStatus.ALL_VALID
    assert result.valid_count == 6
    voltage = next(item for item in result.attribute_summaries if item.attribute_name == "voltage")
    assert voltage.valid_candidate_count == 2 and voltage.candidate_count == 2
    assert [item.normalized_value for item in result.assessments[1:3]] == ["415", "440"]


@pytest.mark.parametrize(
    ("value", "status", "issue"),
    [
        ("92", CandidateValidationStatus.VALID, None),
        ("0", CandidateValidationStatus.VALID, None),
        ("100", CandidateValidationStatus.VALID, None),
        ("105", CandidateValidationStatus.INVALID, ValidationIssueType.NUMERIC_MAX_VIOLATION),
        ("-1", CandidateValidationStatus.INVALID, ValidationIssueType.NUMERIC_MIN_VIOLATION),
    ],
)
def test_efficiency_inclusive_range(value, status, issue) -> None:
    assessment = validate(("efficiency", value, "%")).assessments[0]
    assert assessment.status is status
    assert (assessment.issues[0].issue_type if assessment.issues else None) is issue


@pytest.mark.parametrize(
    ("value", "status"),
    [
        ("1", CandidateValidationStatus.VALID),
        ("3", CandidateValidationStatus.VALID),
        ("2", CandidateValidationStatus.INVALID),
    ],
)
def test_phase_allowed_values(value, status) -> None:
    assessment = validate(("phase", value, None)).assessments[0]
    assert assessment.status is status
    if status is CandidateValidationStatus.INVALID:
        assert assessment.issues[0].issue_type is ValidationIssueType.ALLOWED_VALUE_VIOLATION


@pytest.mark.parametrize(
    ("value", "status"),
    [
        ("IP55", CandidateValidationStatus.VALID),
        ("IP66", CandidateValidationStatus.VALID),
        ("IP55W", CandidateValidationStatus.VALID),
        ("P55", CandidateValidationStatus.INVALID),
        ("IP5", CandidateValidationStatus.INVALID),
    ],
)
def test_ip_rating_pattern_and_plain_text(value, status) -> None:
    assessment = validate(("ipRating", value, None)).assessments[0]
    assert assessment.status is status
    if status is CandidateValidationStatus.INVALID:
        assert assessment.issues[0].issue_type is ValidationIssueType.PATTERN_VIOLATION
    assert validate(("insulationClass", "Mechanical Seal", None)).valid_count == 1


def test_units_invalid_normalization_and_fractional_integer() -> None:
    missing = validate(("ratedPower", "5.5", None)).assessments[0]
    assert missing.status is CandidateValidationStatus.VALID_WITH_WARNINGS
    assert missing.issues[0].issue_type is ValidationIssueType.UNIT_MISSING
    assert missing.issues[0].severity is ValidationIssueSeverity.WARNING

    unsupported = validate(("voltage", "415", "rpm")).assessments[0]
    assert unsupported.status is CandidateValidationStatus.INVALID
    assert ValidationIssueType.UNIT_UNSUPPORTED in {item.issue_type for item in unsupported.issues}

    schema, invalid_result = normalized(("voltage", "bad", "V"))
    invalid = (
        AttributeValidationEngine()
        .validate(job_id=uuid4(), normalization_result=invalid_result, schema=schema, now=NOW)
        .assessments[0]
    )
    assert invalid.status is CandidateValidationStatus.NOT_VALIDATABLE
    assert invalid.issues[0].issue_type is ValidationIssueType.NORMALIZATION_INVALID

    schema, integer_result = normalized(("speedRpm", "1440", "rpm"))
    fractional = replace(
        integer_result.candidates[0],
        normalized_value="3.5",
        normalization_status=NormalizationStatus.RAW_TEXT_PRESERVED,
    )
    adjusted = AttributeNormalizationResult.create(
        job_id=uuid4(),
        product_id=integer_result.product_id,
        extraction_id=integer_result.extraction_id,
        classification_id=integer_result.classification_id,
        category=integer_result.category,
        schema_version=integer_result.schema_version,
        schema_fingerprint=integer_result.schema_fingerprint,
        candidates=(fractional,),
        now=NOW,
    )
    assessed = (
        AttributeValidationEngine()
        .validate(job_id=uuid4(), normalization_result=adjusted, schema=schema, now=NOW)
        .assessments[0]
    )
    assert assessed.status is CandidateValidationStatus.INVALID
    assert assessed.issues[0].message_code == "INTEGER_REQUIRED"


def test_zero_and_all_invalid_candidates_have_no_validatable_status() -> None:
    schema, base = normalized(("voltage", "415", "V"))
    empty = AttributeNormalizationResult.create(
        job_id=uuid4(),
        product_id=base.product_id,
        extraction_id=base.extraction_id,
        classification_id=base.classification_id,
        category=base.category,
        schema_version=base.schema_version,
        schema_fingerprint=base.schema_fingerprint,
        candidates=(),
        now=NOW,
    )
    assert (
        AttributeValidationEngine()
        .validate(job_id=uuid4(), normalization_result=empty, schema=schema, now=NOW)
        .status
        is AttributeValidationResultStatus.NO_VALIDATABLE_CANDIDATES
    )
    assert (
        validate(("voltage", "bad", "V")).status
        is AttributeValidationResultStatus.NO_VALIDATABLE_CANDIDATES
    )


def test_malformed_pattern_unknown_attribute_and_limits_are_technical_failures() -> None:
    schema, result = normalized(("ipRating", "IP55", None))
    definitions = tuple(
        replace(item, validation_rules=AttributeValidationRules(pattern="["))
        if item.canonical_name == "ipRating"
        else item
        for item in schema.attributes
    )
    malformed = CategoryAttributeSchema.create(
        category=schema.category,
        version=schema.version,
        status=schema.status,
        description=schema.description,
        attributes=definitions,
        now=NOW,
    )
    result = replace(
        result,
        schema_fingerprint=malformed.schema_fingerprint,
        candidates=tuple(
            replace(item, schema_fingerprint=malformed.schema_fingerprint)
            for item in result.candidates
        ),
    )
    with pytest.raises(AttributeValidationSchemaRuleInvalidError):
        AttributeValidationEngine().validate(
            job_id=uuid4(), normalization_result=result, schema=malformed, now=NOW
        )
    original_schema, original = normalized(("voltage", "415", "V"))
    unknown_candidate = replace(original.candidates[0], attribute_name="unknownField")
    unknown = replace(original, candidates=(unknown_candidate,))
    with pytest.raises(AttributeValidationUnknownAttributeError):
        AttributeValidationEngine().validate(
            job_id=uuid4(), normalization_result=unknown, schema=original_schema, now=NOW
        )
    with pytest.raises(AttributeValidationCandidateLimitExceededError):
        AttributeValidationEngine(max_candidates=1).validate(
            job_id=uuid4(),
            normalization_result=replace(
                original,
                candidates=(original.candidates[0], original.candidates[0]),
                candidate_count=2,
                normalized_count=2,
            ),
            schema=original_schema,
            now=NOW,
        )
    with pytest.raises(AttributeValidationAttributeLimitExceededError):
        AttributeValidationEngine(max_attributes=1).validate(
            job_id=uuid4(), normalization_result=original, schema=original_schema, now=NOW
        )
    oversized_candidate = replace(original.candidates[0], normalized_value="1" * 21)
    oversized = replace(original, candidates=(oversized_candidate,))
    with pytest.raises(AttributeValidationValueLimitExceededError):
        AttributeValidationEngine(max_value_characters=20).validate(
            job_id=uuid4(), normalization_result=oversized, schema=original_schema, now=NOW
        )
    _, unsupported = normalized(("voltage", "415", "rpm"))
    with pytest.raises(AttributeValidationIssueLimitExceededError):
        AttributeValidationEngine(max_issues_per_candidate=1).validate(
            job_id=uuid4(), normalization_result=unsupported, schema=original_schema, now=NOW
        )
