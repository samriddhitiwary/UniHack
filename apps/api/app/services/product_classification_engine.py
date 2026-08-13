"""Deterministic, explainable product classification rules."""

import re
from collections.abc import Sequence

from app.core.exceptions import ProductClassificationMatchLimitExceededError
from app.domain.product_classification import (
    ClassificationEvidence,
    ClassificationMatch,
    ClassificationSignalStrength,
    ProductClassificationDecision,
    ProductClassificationStatus,
)
from app.domain.products import ProductCategory

MINIMUM_SCORE = 1_000
MINIMUM_MARGIN = 300

_PUMP_SIGNALS = (
    ("centrifugal pump", ClassificationSignalStrength.STRONG),
    ("mechanical seal", ClassificationSignalStrength.MEDIUM),
    ("flow rate", ClassificationSignalStrength.MEDIUM),
    ("pump speed", ClassificationSignalStrength.MEDIUM),
    ("delivery head", ClassificationSignalStrength.MEDIUM),
    ("shutoff head", ClassificationSignalStrength.MEDIUM),
    ("npsh", ClassificationSignalStrength.MEDIUM),
    ("impeller", ClassificationSignalStrength.MEDIUM),
    ("suction", ClassificationSignalStrength.MEDIUM),
    ("discharge", ClassificationSignalStrength.MEDIUM),
    ("pump", ClassificationSignalStrength.WEAK),
    ("head", ClassificationSignalStrength.WEAK),
    ("flow", ClassificationSignalStrength.WEAK),
    ("inlet", ClassificationSignalStrength.WEAK),
    ("outlet", ClassificationSignalStrength.WEAK),
)
_MOTOR_SIGNALS = (
    ("induction motor", ClassificationSignalStrength.STRONG),
    ("three phase", ClassificationSignalStrength.STRONG),
    ("3 phase", ClassificationSignalStrength.STRONG),
    ("3-phase", ClassificationSignalStrength.STRONG),
    ("rated power", ClassificationSignalStrength.MEDIUM),
    ("rated output", ClassificationSignalStrength.MEDIUM),
    ("revolutions per minute", ClassificationSignalStrength.MEDIUM),
    ("power factor", ClassificationSignalStrength.MEDIUM),
    ("cos phi", ClassificationSignalStrength.MEDIUM),
    ("insulation class", ClassificationSignalStrength.MEDIUM),
    ("ip rating", ClassificationSignalStrength.MEDIUM),
    ("synchronous speed", ClassificationSignalStrength.MEDIUM),
    ("efficiency", ClassificationSignalStrength.MEDIUM),
    ("motor", ClassificationSignalStrength.WEAK),
    ("rpm", ClassificationSignalStrength.WEAK),
    ("frequency", ClassificationSignalStrength.WEAK),
    ("hz", ClassificationSignalStrength.WEAK),
    ("voltage", ClassificationSignalStrength.WEAK),
    ("current", ClassificationSignalStrength.WEAK),
    ("ampere", ClassificationSignalStrength.WEAK),
    ("frame", ClassificationSignalStrength.WEAK),
)


def _contains(text: str, signal: str) -> bool:
    return re.search(r"(?<![\w])" + re.escape(signal) + r"(?![\w])", text) is not None


class ProductClassificationEngine:
    def __init__(self, *, max_matches: int = 1_000) -> None:
        if max_matches < 1:
            raise ValueError("max_matches must be positive")
        self._max_matches = max_matches

    def classify(self, evidence: Sequence[ClassificationEvidence]) -> ProductClassificationDecision:
        matches: list[ClassificationMatch] = []
        scores = {
            ProductCategory.CENTRIFUGAL_PUMP: 0,
            ProductCategory.INDUCTION_MOTOR: 0,
        }
        strong_sources: dict[ProductCategory, set[object]] = {
            ProductCategory.CENTRIFUGAL_PUMP: set(),
            ProductCategory.INDUCTION_MOTOR: set(),
        }
        for item in evidence:
            normalized = " ".join(item.text.lower().split())
            for category, signals in (
                (ProductCategory.CENTRIFUGAL_PUMP, _PUMP_SIGNALS),
                (ProductCategory.INDUCTION_MOTOR, _MOTOR_SIGNALS),
            ):
                for signal, strength in signals:
                    if not _contains(normalized, signal):
                        continue
                    weighted_score = int(strength) * item.weight
                    if weighted_score <= 0:
                        continue
                    if len(matches) >= self._max_matches:
                        raise ProductClassificationMatchLimitExceededError(
                            "meaningful classification matches exceed configured maximum"
                        )
                    match = ClassificationMatch(
                        match_id=f"match-{len(matches) + 1:06d}",
                        evidence_id=item.evidence_id,
                        source_id=item.source_id,
                        evidence_type=item.evidence_type,
                        category=category,
                        matched_signal=signal,
                        signal_strength=strength,
                        weighted_score=weighted_score,
                        location=item.location,
                        excerpt=item.text[:500],
                    )
                    matches.append(match)
                    scores[category] += weighted_score
                    if strength is ClassificationSignalStrength.STRONG:
                        strong_sources[category].add(item.source_id)

        pump = scores[ProductCategory.CENTRIFUGAL_PUMP]
        motor = scores[ProductCategory.INDUCTION_MOTOR]
        conflicting_sources = {
            (pump_source, motor_source)
            for pump_source in strong_sources[ProductCategory.CENTRIFUGAL_PUMP]
            for motor_source in strong_sources[ProductCategory.INDUCTION_MOTOR]
            if pump_source != motor_source
        }
        conflict_count = len(conflicting_sources)
        if conflict_count:
            category = ProductCategory.UNCLASSIFIED
            status = ProductClassificationStatus.CONFLICTING_EVIDENCE
            confidence = 0
        else:
            winner = max(pump, motor)
            runner_up = min(pump, motor)
            margin = winner - runner_up
            confidence = min(10_000, margin * 10_000 // max(winner, MINIMUM_SCORE))
            if winner < MINIMUM_SCORE:
                category = ProductCategory.UNCLASSIFIED
                status = ProductClassificationStatus.INSUFFICIENT_EVIDENCE
                confidence = 0
            elif margin < MINIMUM_MARGIN:
                category = ProductCategory.UNCLASSIFIED
                status = ProductClassificationStatus.AMBIGUOUS
            else:
                category = (
                    ProductCategory.CENTRIFUGAL_PUMP
                    if pump > motor
                    else ProductCategory.INDUCTION_MOTOR
                )
                status = ProductClassificationStatus.CLASSIFIED
        return ProductClassificationDecision(
            category=category,
            status=status,
            confidence_bp=confidence,
            pump_score=pump,
            motor_score=motor,
            conflicting_evidence_count=conflict_count,
            matches=tuple(matches),
        )
