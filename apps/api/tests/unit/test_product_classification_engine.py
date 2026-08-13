"""Deterministic classification rule and confidence tests."""

from uuid import uuid4

import pytest

from app.core.exceptions import ProductClassificationMatchLimitExceededError
from app.domain.product_classification import (
    ClassificationEvidence,
    ClassificationEvidenceType,
    ProductClassificationStatus,
)
from app.domain.products import ProductCategory
from app.services.product_classification_engine import ProductClassificationEngine


def evidence(text: str, *, source_id=None, weight: int = 100) -> ClassificationEvidence:
    return ClassificationEvidence(
        evidence_id="evidence-000001",
        source_id=source_id or uuid4(),
        evidence_type=ClassificationEvidenceType.DIRECT_TEXT,
        text=text,
        location="sourceId=test",
        weight=weight,
    )


def test_classifies_explicit_centrifugal_pump_deterministically() -> None:
    engine = ProductClassificationEngine()
    first = engine.classify((evidence("Centrifugal pump"),))
    second = engine.classify((evidence("Centrifugal pump", source_id=first.matches[0].source_id),))
    assert first.category is ProductCategory.CENTRIFUGAL_PUMP
    assert first.status is ProductClassificationStatus.CLASSIFIED
    assert first.pump_score == 1_100  # phrase plus bounded generic word match
    assert first.confidence_bp == 10_000
    assert first.pump_score == second.pump_score


def test_classifies_explicit_induction_motor_and_avoids_motorcycle() -> None:
    engine = ProductClassificationEngine()
    motor = engine.classify((evidence("Three phase induction motor"),))
    motorcycle = engine.classify((evidence("motorcycle frame"),))
    assert motor.category is ProductCategory.INDUCTION_MOTOR
    assert motor.status is ProductClassificationStatus.CLASSIFIED
    assert motorcycle.category is ProductCategory.UNCLASSIFIED
    assert motorcycle.motor_score == 100


def test_weak_or_irrelevant_evidence_is_insufficient() -> None:
    decision = ProductClassificationEngine().classify((evidence("Industrial model XJ-100"),))
    assert decision.category is ProductCategory.UNCLASSIFIED
    assert decision.status is ProductClassificationStatus.INSUFFICIENT_EVIDENCE
    assert decision.confidence_bp == 0


def test_close_scores_are_ambiguous() -> None:
    decision = ProductClassificationEngine().classify(
        (evidence("centrifugal pump induction motor", weight=100),)
    )
    assert decision.status is ProductClassificationStatus.AMBIGUOUS
    assert decision.category is ProductCategory.UNCLASSIFIED


def test_strong_different_source_signals_are_conflicting() -> None:
    decision = ProductClassificationEngine().classify(
        (evidence("centrifugal pump"), evidence("induction motor"))
    )
    assert decision.status is ProductClassificationStatus.CONFLICTING_EVIDENCE
    assert decision.category is ProductCategory.UNCLASSIFIED
    assert decision.conflicting_evidence_count == 1


def test_match_limit_fails_instead_of_truncating() -> None:
    with pytest.raises(ProductClassificationMatchLimitExceededError):
        ProductClassificationEngine(max_matches=1).classify(
            (evidence("centrifugal pump impeller"),)
        )
