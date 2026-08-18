"""Completed-review fixtures for reviewed attribute materialization tests."""

from dataclasses import replace
from uuid import uuid4

from app.domain.category_schemas.builtins import centrifugal_pump_schema_v1
from app.domain.product_review import (
    AttributeReviewDecision,
    AttributeReviewDecisionType,
    CurrentAttributeReviewDecision,
    ProductReviewSession,
)
from app.services.attribute_completeness_engine import AttributeCompletenessEngine
from app.services.attribute_conflict_detection_engine import AttributeConflictDetectionEngine
from app.services.attribute_normalization_engine import AttributeNormalizationEngine
from app.services.attribute_selection_engine import AttributeSelectionEngine
from app.services.attribute_validation_engine import AttributeValidationEngine
from tests.fixtures.attribute_normalization import NOW, candidate, extraction
from tests.unit.test_attribute_selection_engine import attr, pipeline

REQUIRED = (
    ("ratedPower", "5.5", "kW"),
    ("voltage", "415", "V"),
    ("frequency", "50", "Hz"),
    ("speedRpm", "1440", "rpm"),
    ("phase", "3", None),
)


def completed_review(
    *,
    conflict_voltage: bool = False,
    manual_voltage: bool = False,
    warning_power: bool = False,
):
    items = []
    for value in REQUIRED:
        if value[0] == "voltage" and conflict_voltage:
            items.extend((("voltage", "415", "V"), ("voltage", "440", "V")))
        elif value[0] == "ratedPower" and warning_power:
            items.extend((("ratedPower", "5.5", None), ("ratedPower", "5.5", None)))
        else:
            items.extend((value, value))
    schema, normalization, conflict, validation, completeness, selection = pipeline(*items)
    review = ProductReviewSession.create(selection, NOW)
    decisions = []
    for index, definition in enumerate((a for a in schema.attributes if a.required), 1):
        proposal = attr(selection, definition.canonical_name)
        candidate_id = proposal.primary_candidate_id
        decision_type = AttributeReviewDecisionType.APPROVE_PROPOSED
        value, unit = proposal.proposed_value, proposal.proposed_unit
        raw_value = raw_unit = None
        if definition.canonical_name == "voltage" and conflict_voltage:
            candidate_id = proposal.review_candidate_ids[-1]
            candidate = next(
                c for c in normalization.candidates if c.normalized_candidate_id == candidate_id
            )
            value, unit = candidate.normalized_value, candidate.normalized_unit
            decision_type = AttributeReviewDecisionType.APPROVE_CANDIDATE
        if definition.canonical_name == "voltage" and manual_voltage:
            candidate_id, value, unit = None, "430", "V"
            raw_value, raw_unit = "430", "V"
            decision_type = AttributeReviewDecisionType.MANUAL_OVERRIDE
        if definition.canonical_name == "ratedPower" and warning_power:
            candidate_id = proposal.review_candidate_ids[0]
            selected_candidate = next(
                c for c in normalization.candidates if c.normalized_candidate_id == candidate_id
            )
            value, unit = selected_candidate.normalized_value, selected_candidate.normalized_unit
            decision_type = AttributeReviewDecisionType.APPROVE_CANDIDATE
        decisions.append(
            AttributeReviewDecision(
                decision_id=uuid4(),
                review_id=review.review_id,
                product_id=review.product_id,
                decision_sequence=index,
                attribute_name=definition.canonical_name,
                decision_type=decision_type,
                candidate_id=candidate_id,
                approved_value=value,
                approved_unit=unit,
                manual_raw_value=raw_value,
                manual_raw_unit=raw_unit,
                comment=None,
                reviewer_id="reviewer-local-001",
                review_version=index + 1,
                created_at=NOW,
            )
        )
    review = replace(
        review,
        version=len(decisions) + 1,
        decision_count=len(decisions),
        required_resolved_count=len(decisions),
        required_unresolved_count=0,
    )
    review = review.complete(NOW)
    current = tuple(CurrentAttributeReviewDecision.from_decision(item) for item in decisions)
    return (
        schema,
        normalization,
        conflict,
        validation,
        completeness,
        selection,
        review,
        tuple(decisions),
        current,
    )


def completed_pump_review():
    schema = centrifugal_pump_schema_v1()
    values = {
        "flowRate": ("12", "m3/h"),
        "head": ("30", "m"),
        "ratedPower": ("4", "kW"),
    }
    required = tuple(attribute for attribute in schema.attributes if attribute.required)
    sources = tuple(
        candidate(
            schema,
            definition.canonical_name,
            values[definition.canonical_name][0],
            values[definition.canonical_name][1],
            index=index,
        )
        for index, definition in enumerate((*required, *required), 1)
    )
    normalization = AttributeNormalizationEngine().normalize(
        job_id=uuid4(), extraction_result=extraction(schema, sources), schema=schema, now=NOW
    )
    conflict = AttributeConflictDetectionEngine().detect(
        job_id=uuid4(), normalization_result=normalization, now=NOW
    )
    validation = AttributeValidationEngine().validate(
        job_id=uuid4(), normalization_result=normalization, schema=schema, now=NOW
    )
    completeness = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(), conflict_result=conflict, schema=schema, now=NOW
    )
    selection = AttributeSelectionEngine().select(
        job_id=uuid4(),
        conflict_result=conflict,
        validation_result=validation,
        completeness_result=completeness,
        normalization_result=normalization,
        now=NOW,
    )
    review = ProductReviewSession.create(selection, NOW)
    decisions = tuple(
        AttributeReviewDecision(
            decision_id=uuid4(),
            review_id=review.review_id,
            product_id=review.product_id,
            decision_sequence=index,
            attribute_name=definition.canonical_name,
            decision_type=AttributeReviewDecisionType.APPROVE_PROPOSED,
            candidate_id=(
                proposal := next(
                    item
                    for item in selection.attributes
                    if item.attribute_name == definition.canonical_name
                )
            ).primary_candidate_id,
            approved_value=proposal.proposed_value,
            approved_unit=proposal.proposed_unit,
            manual_raw_value=None,
            manual_raw_unit=None,
            comment=None,
            reviewer_id="reviewer-local-001",
            review_version=index + 1,
            created_at=NOW,
        )
        for index, definition in enumerate(required, 1)
    )
    review = replace(
        review,
        version=len(decisions) + 1,
        decision_count=len(decisions),
        required_resolved_count=len(decisions),
        required_unresolved_count=0,
    ).complete(NOW)
    current = tuple(CurrentAttributeReviewDecision.from_decision(item) for item in decisions)
    return (
        schema,
        normalization,
        conflict,
        validation,
        completeness,
        selection,
        review,
        decisions,
        current,
    )
