from dataclasses import replace
from uuid import uuid4

import pytest

from app.core.exceptions import (
    AttributeCompletenessAttributeLimitExceededError,
    AttributeCompletenessCandidateIdLimitExceededError,
    AttributeCompletenessSchemaMismatchError,
)
from app.domain.attribute_completeness import (
    AttributeCompletenessState,
    AttributeCompletenessStatus,
    percentage_basis_points,
)
from app.domain.attribute_conflicts import AttributeConsensusStatus
from app.domain.attribute_normalization import AttributeNormalizationResult
from app.domain.category_schemas.builtins import (
    centrifugal_pump_schema_v1,
    induction_motor_schema_v1,
)
from app.services.attribute_completeness_engine import AttributeCompletenessEngine
from app.services.attribute_conflict_detection_engine import AttributeConflictDetectionEngine
from app.services.attribute_normalization_engine import AttributeNormalizationEngine
from tests.fixtures.attribute_normalization import NOW, candidate, extraction


def conflict_for(*names):
    schema = induction_motor_schema_v1()
    sources = tuple(
        candidate(schema, name, value, unit, index=i)
        for i, (name, value, unit) in enumerate(names, 1)
    )
    normalized = AttributeNormalizationEngine().normalize(
        job_id=uuid4(), extraction_result=extraction(schema, sources), schema=schema, now=NOW
    )
    conflict = AttributeConflictDetectionEngine().detect(
        job_id=uuid4(), normalization_result=normalized, now=NOW
    )
    return schema, conflict


def test_missing_required_and_optional_are_separate() -> None:
    schema, conflict = conflict_for(("ratedPower", "5.5", "kW"))
    result = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(), conflict_result=conflict, schema=schema, now=NOW
    )
    assert result.status is AttributeCompletenessStatus.INCOMPLETE
    assert result.required_missing_count == result.required_attribute_count - 1
    assert result.optional_missing_count == result.optional_attribute_count
    assert result.attributes[0].state is AttributeCompletenessState.PRESENT_SINGLE_SOURCE


def test_conflict_takes_precedence_and_preserves_candidates() -> None:
    schema, conflict = conflict_for(("voltage", "415", "V"), ("voltage", "440", "V"))
    result = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(), conflict_result=conflict, schema=schema, now=NOW
    )
    voltage = next(item for item in result.attributes if item.attribute_name == "voltage")
    assert result.status is AttributeCompletenessStatus.CONFLICTED
    assert voltage.state is AttributeCompletenessState.CONFLICTED
    assert voltage.available and not voltage.resolved and not voltage.verified
    assert voltage.candidate_ids == conflict.attributes[0].candidate_ids


def test_all_consensus_mappings_and_verifiedness() -> None:
    schema, conflict = conflict_for(("ratedPower", "5.5", "kW"))
    source = conflict.attributes[0]
    mappings = {
        AttributeConsensusStatus.AGREEMENT: AttributeCompletenessState.PRESENT,
        AttributeConsensusStatus.AGREEMENT_WITH_TOLERANCE: (
            AttributeCompletenessState.PRESENT_WITH_TOLERANCE
        ),
        AttributeConsensusStatus.SINGLE_CANDIDATE: (
            AttributeCompletenessState.PRESENT_SINGLE_SOURCE
        ),
        AttributeConsensusStatus.CONFLICT: AttributeCompletenessState.CONFLICTED,
        AttributeConsensusStatus.INDETERMINATE: AttributeCompletenessState.INDETERMINATE,
        AttributeConsensusStatus.NO_VALID_CANDIDATES: AttributeCompletenessState.INVALID_ONLY,
    }
    engine = AttributeCompletenessEngine()
    for status, state in mappings.items():
        adjusted = replace(source, status=status)
        aggregate = replace(
            conflict,
            attributes=(adjusted,),
            agreement_count=int(status is AttributeConsensusStatus.AGREEMENT),
            tolerance_agreement_count=int(
                status is AttributeConsensusStatus.AGREEMENT_WITH_TOLERANCE
            ),
            single_candidate_count=int(status is AttributeConsensusStatus.SINGLE_CANDIDATE),
            conflict_count=int(status is AttributeConsensusStatus.CONFLICT),
            indeterminate_count=int(status is AttributeConsensusStatus.INDETERMINATE),
            no_valid_candidate_count=int(status is AttributeConsensusStatus.NO_VALID_CANDIDATES),
        )
        item = engine.evaluate(
            job_id=uuid4(), conflict_result=aggregate, schema=schema, now=NOW
        ).attributes[0]
        assert item.state is state
    assert percentage_basis_points(2, 3) == 6666
    assert percentage_basis_points(0, 0) == 10000


def test_engine_rejects_invalid_limits_lineage_and_candidate_bounds() -> None:
    with pytest.raises(ValueError):
        AttributeCompletenessEngine(max_attributes=0)
    schema, conflict = conflict_for(("voltage", "415", "V"))
    with pytest.raises(AttributeCompletenessAttributeLimitExceededError):
        AttributeCompletenessEngine(max_attributes=1).evaluate(
            job_id=uuid4(), conflict_result=conflict, schema=schema, now=NOW
        )
    with pytest.raises(AttributeCompletenessCandidateIdLimitExceededError):
        _, two_candidates = conflict_for(("voltage", "415", "V"), ("voltage", "440", "V"))
        AttributeCompletenessEngine(max_candidate_ids_per_attribute=1).evaluate(
            job_id=uuid4(),
            conflict_result=two_candidates,
            schema=schema,
            now=NOW,
        )
    with pytest.raises(AttributeCompletenessSchemaMismatchError):
        AttributeCompletenessEngine().evaluate(
            job_id=uuid4(),
            conflict_result=replace(conflict, schema_fingerprint="f" * 64),
            schema=schema,
            now=NOW,
        )


def _result_with_required_statuses(schema, statuses):
    _, base = conflict_for(("ratedPower", "5.5", "kW"))
    source = base.attributes[0]
    required = [item for item in schema.attributes if item.required]
    attributes = tuple(
        replace(
            source,
            attribute_name=definition.canonical_name,
            attribute_display_name=definition.display_name,
            data_type=definition.data_type,
            status=status,
        )
        for definition, status in zip(required, statuses, strict=True)
    )
    return replace(
        base,
        category=schema.category,
        schema_version=schema.version,
        schema_fingerprint=schema.schema_fingerprint,
        attributes=attributes,
        attribute_count=len(attributes),
        agreement_count=sum(
            item.status is AttributeConsensusStatus.AGREEMENT for item in attributes
        ),
        tolerance_agreement_count=sum(
            item.status is AttributeConsensusStatus.AGREEMENT_WITH_TOLERANCE for item in attributes
        ),
        single_candidate_count=sum(
            item.status is AttributeConsensusStatus.SINGLE_CANDIDATE for item in attributes
        ),
        conflict_count=sum(item.status is AttributeConsensusStatus.CONFLICT for item in attributes),
        indeterminate_count=sum(
            item.status is AttributeConsensusStatus.INDETERMINATE for item in attributes
        ),
        no_valid_candidate_count=sum(
            item.status is AttributeConsensusStatus.NO_VALID_CANDIDATES for item in attributes
        ),
    )


def test_complete_motor_and_single_source_verifiedness() -> None:
    schema = induction_motor_schema_v1()
    statuses = [AttributeConsensusStatus.AGREEMENT] * sum(
        item.required for item in schema.attributes
    )
    conflict = _result_with_required_statuses(schema, statuses)
    complete = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(), conflict_result=conflict, schema=schema, now=NOW
    )
    assert complete.status is AttributeCompletenessStatus.COMPLETE
    assert complete.required_resolved_bp == complete.required_verified_bp == 10_000

    statuses[-1] = AttributeConsensusStatus.SINGLE_CANDIDATE
    single = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(),
        conflict_result=_result_with_required_statuses(schema, statuses),
        schema=schema,
        now=NOW,
    )
    assert single.status is AttributeCompletenessStatus.COMPLETE_WITH_SINGLE_SOURCE
    assert single.required_resolved_bp == 10_000 and single.required_verified_bp < 10_000


@pytest.mark.parametrize("missing_count", [1, 2])
def test_one_or_multiple_required_attributes_missing(missing_count) -> None:
    schema = induction_motor_schema_v1()
    required_count = sum(item.required for item in schema.attributes)
    complete = _result_with_required_statuses(
        schema, [AttributeConsensusStatus.AGREEMENT] * required_count
    )
    conflict = replace(
        complete,
        attributes=complete.attributes[:-missing_count],
        attribute_count=required_count - missing_count,
        agreement_count=required_count - missing_count,
    )
    result = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(), conflict_result=conflict, schema=schema, now=NOW
    )
    assert result.status is AttributeCompletenessStatus.INCOMPLETE
    assert result.required_missing_count == missing_count


def test_optional_conflict_does_not_downgrade_complete_required_attributes() -> None:
    schema = induction_motor_schema_v1()
    required_count = sum(item.required for item in schema.attributes)
    base = _result_with_required_statuses(
        schema, [AttributeConsensusStatus.AGREEMENT] * required_count
    )
    optional = next(item for item in schema.attributes if not item.required)
    optional_conflict = replace(
        base.attributes[0],
        attribute_name=optional.canonical_name,
        attribute_display_name=optional.display_name,
        data_type=optional.data_type,
        status=AttributeConsensusStatus.CONFLICT,
    )
    conflict = replace(
        base,
        attributes=(*base.attributes, optional_conflict),
        attribute_count=required_count + 1,
        conflict_count=1,
    )
    result = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(), conflict_result=conflict, schema=schema, now=NOW
    )
    assert result.status is AttributeCompletenessStatus.COMPLETE
    assert result.optional_conflicted_count == 1


def test_pump_half_complete_and_no_usable_statuses() -> None:
    schema = centrifugal_pump_schema_v1()
    required_count = sum(item.required for item in schema.attributes)
    statuses = [AttributeConsensusStatus.AGREEMENT] + [
        AttributeConsensusStatus.NO_VALID_CANDIDATES
    ] * (required_count - 1)
    result = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(),
        conflict_result=_result_with_required_statuses(schema, statuses),
        schema=schema,
        now=NOW,
    )
    assert result.status is AttributeCompletenessStatus.INCOMPLETE
    assert result.required_resolved_bp == 10_000 // required_count

    unusable = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(),
        conflict_result=_result_with_required_statuses(
            schema, [AttributeConsensusStatus.NO_VALID_CANDIDATES] * required_count
        ),
        schema=schema,
        now=NOW,
    )
    assert unusable.status is AttributeCompletenessStatus.NO_USABLE_ATTRIBUTES


def test_unsupported_unit_only_is_invalid_not_missing() -> None:
    schema, conflict = conflict_for(("voltage", "415", "rpm"))
    result = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(), conflict_result=conflict, schema=schema, now=NOW
    )
    voltage = next(item for item in result.attributes if item.attribute_name == "voltage")
    assert voltage.state is AttributeCompletenessState.INVALID_ONLY
    assert voltage.candidate_count == 1 and not voltage.available


def test_unit_missing_evidence_is_indeterminate_not_missing() -> None:
    schema, conflict = conflict_for(("ratedPower", "5.5", None), ("ratedPower", "5.5", "kW"))
    result = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(), conflict_result=conflict, schema=schema, now=NOW
    )
    power = next(item for item in result.attributes if item.attribute_name == "ratedPower")
    assert power.state is AttributeCompletenessState.INDETERMINATE
    assert power.available and not power.resolved


def test_no_candidate_product_has_only_missing_attributes() -> None:
    schema, base = conflict_for(("voltage", "415", "V"))
    normalized = AttributeNormalizationResult.create(
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
    conflict = AttributeConflictDetectionEngine().detect(
        job_id=uuid4(), normalization_result=normalized, now=NOW
    )
    result = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(), conflict_result=conflict, schema=schema, now=NOW
    )
    assert result.status is AttributeCompletenessStatus.NO_USABLE_ATTRIBUTES
    assert result.total_missing_count == result.total_attribute_count
    assert all(item.state is AttributeCompletenessState.MISSING for item in result.attributes)
