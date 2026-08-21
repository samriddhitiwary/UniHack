"""Signal, measurement, resolver, classification, and attribute tests."""

from fractions import Fraction

import pytest

from app.domain.unilog_challenge import (
    ObservedVocabulary,
    ResolutionStatus,
    UnilogMeasurementCandidate,
    UnilogSemanticAttributeCandidate,
)
from app.services.unilog_challenge.attribute_extractor import UnilogAttributeExtractor
from app.services.unilog_challenge.brand_resolver import UnilogChallengeBrandResolver
from app.services.unilog_challenge.classifier import UnilogChallengeClassifier
from app.services.unilog_challenge.description_signal_extractor import (
    UnilogDescriptionSignalExtractor,
)
from app.services.unilog_challenge.manufacturer_resolver import (
    UnilogChallengeManufacturerResolver,
)
from app.services.unilog_challenge.measurement_parser import (
    parse_measurements,
    parse_trade_fraction,
)
from tests.unit.unilog_challenge.helpers import challenge_row


def vocabulary() -> ObservedVocabulary:
    return ObservedVocabulary(
        manufacturers=frozenset({"Whirlpool Corporation", "Rheem Manufacturing"}),
        brands=frozenset({"Whirlpool®", "FRIGIDAIRE®"}),
        classpaths=frozenset(
            {"Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers"}
        ),
        attribute_labels=frozenset({"Series", "Material"}),
        uoms=frozenset({"in", "V", "A", "dBA"}),
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1/2", Fraction(1, 2)),
        ("3/8", Fraction(3, 8)),
        ("1-1/4", Fraction(5, 4)),
        ("50-1/4", Fraction(201, 4)),
        ("18", Fraction(18)),
        ("2.5", Fraction(5, 2)),
    ],
)
def test_trade_fraction_parsing_is_exact(raw: str, expected: Fraction) -> None:
    assert parse_trade_fraction(raw) == expected


def test_measurements_parse_quoted_dimensions_with_spans() -> None:
    text = 'Belt 1/2"x18" P150'
    parsed = parse_measurements(text)
    assert [(item.exact_value, item.normalized_unit) for item in parsed] == [
        ("1/2", "in"),
        ("18", "in"),
    ]
    assert [text[start:end] for start, end in (item.evidence_span for item in parsed)] == [
        '1/2"',
        '18"',
    ]


def test_unmarked_dimensions_require_an_explicit_context_unit() -> None:
    assert parse_measurements("Belt 1/2 x 18") == ()
    parsed = parse_measurements("Belt 1/2 x 18", implicit_dimension_unit="in")
    assert [item.exact_value for item in parsed] == ["1/2", "18"]
    assert all(item.confidence_bp == 8_500 for item in parsed)


def test_measurement_candidate_validates_and_formats_mixed_numbers() -> None:
    candidate = UnilogMeasurementCandidate(
        raw_text='50-1/4"',
        numeric_value=Fraction(201, 4),
        raw_unit='"',
        normalized_unit="in",
        evidence_span=(0, 8),
        confidence_bp=9_500,
    )
    assert candidate.exact_value == "50-1/4"
    with pytest.raises(ValueError, match="evidence span"):
        UnilogMeasurementCandidate(
            raw_text="1",
            numeric_value=Fraction(1),
            raw_unit="in",
            normalized_unit="in",
            evidence_span=(1, 1),
            confidence_bp=9_000,
        )


def test_signal_extraction_preserves_product_attribute_and_measurement_evidence() -> None:
    row = challenge_row()
    signals = UnilogDescriptionSignalExtractor().extract(row)
    assert signals.product_type == "Sanding Belt"
    assert row.part_desc[slice(*signals.product_type_span)] == "Sanding Belt"
    assert signals.quantity == 6
    assert signals.grit == "P150"
    assert [(item.exact_value, item.normalized_unit) for item in signals.measurements] == [
        ("1/2", "in"),
        ("18", "in"),
    ]


def test_brand_resolution_uses_agreement_and_preserves_conflicts() -> None:
    resolver = UnilogChallengeBrandResolver()
    resolved = resolver.resolve(challenge_row(e1="Diablo", dib="Diablo"))
    assert resolved.value == "Diablo"
    assert resolved.status is ResolutionStatus.RESOLVED
    assert resolved.confidence_bp == 9_500
    conflict = resolver.resolve(challenge_row(e1="Diablo", dib="Other"))
    assert conflict.value is None
    assert conflict.status is ResolutionStatus.AMBIGUOUS
    assert conflict.review_required


def test_brand_resolution_never_promotes_placeholders_and_weak_description_is_reviewable() -> None:
    resolver = UnilogChallengeBrandResolver()
    blank = challenge_row(
        e1="-- Unbranded --", description="Generic dishwasher", manufacturer="Unknown"
    )
    assert resolver.resolve(blank, vocabulary()).value is None
    observed = challenge_row(
        e1="-- Unbranded --",
        description="Whirlpool dishwasher",
        manufacturer="Appliance Dealers Cooperative (APPDE)",
    )
    result = resolver.resolve(observed, vocabulary())
    assert result.value == "Whirlpool®"
    assert result.status is ResolutionStatus.PARTIAL
    assert result.review_required


def test_manufacturer_resolution_distinguishes_supplier_and_requires_agreement() -> None:
    brands = UnilogChallengeBrandResolver()
    manufacturers = UnilogChallengeManufacturerResolver()
    supplier = challenge_row(
        description="3M 775L sanding disc",
        e1="3M",
        manufacturer="Jam Industrial Supply LLC (JAM01)",
    )
    ambiguous = manufacturers.resolve(supplier, brands.resolve(supplier))
    assert ambiguous.candidate_manufacturer is None
    assert ambiguous.status is ResolutionStatus.AMBIGUOUS
    agreed = challenge_row(e1="Diablo", manufacturer="Diablo (DIA01)")
    resolved = manufacturers.resolve(agreed, brands.resolve(agreed))
    assert resolved.candidate_manufacturer == "Diablo"
    assert resolved.status is ResolutionStatus.RESOLVED


def test_unknown_manufacturer_does_not_fail_partial_resolution() -> None:
    row = challenge_row(manufacturer="", e1="-- Unbranded --")
    brand = UnilogChallengeBrandResolver().resolve(row)
    result = UnilogChallengeManufacturerResolver().resolve(row, brand)
    assert result.status is ResolutionStatus.MISSING
    assert result.review_required


def test_classifier_only_emits_observed_supported_taxonomy() -> None:
    extractor = UnilogDescriptionSignalExtractor()
    classifier = UnilogChallengeClassifier()
    dishwasher = extractor.extract(challenge_row(description="ABC Dishwasher SS", part="ABC"))
    resolved = classifier.classify(dishwasher, vocabulary())
    assert resolved.classpath is not None
    assert resolved.leaf_node == "Built-In Dishwashers"
    belt = extractor.extract(challenge_row())
    unknown = classifier.classify(belt, vocabulary())
    assert unknown.product_type_candidate == "Sanding Belt"
    assert unknown.classpath is None
    assert unknown.review_required


def test_attribute_extractor_keeps_unknown_labels_internal_and_orders_evidence() -> None:
    signals = UnilogDescriptionSignalExtractor().extract(challenge_row())
    attributes = UnilogAttributeExtractor().extract(signals, vocabulary())
    by_name = {item.semantic_name: item for item in attributes}
    assert by_name["Package Quantity"].official_label is None
    assert by_name["Grit"].normalized_value == "P150"
    assert by_name["Width"].normalized_value == "1/2"
    assert by_name["Length"].normalized_value == "18"
    assert all(not item.review_required for item in attributes)


def test_duplicate_attributes_collapse_and_conflicting_values_require_review() -> None:
    extractor = UnilogAttributeExtractor()
    first = UnilogSemanticAttributeCandidate(
        semantic_name="Material",
        raw_value="Steel",
        normalized_value="Steel",
        uom=None,
        evidence_span=(0, 5),
        fact_id="ATTRIBUTE:Material",
        official_label="Material",
        confidence_bp=9_000,
    )
    duplicate = UnilogSemanticAttributeCandidate(
        semantic_name="Material",
        raw_value="Steel",
        normalized_value="Steel",
        uom=None,
        evidence_span=(10, 15),
        fact_id="ATTRIBUTE:Material",
        official_label="Material",
        confidence_bp=9_000,
    )
    conflict = UnilogSemanticAttributeCandidate(
        semantic_name="Material",
        raw_value="Iron",
        normalized_value="Iron",
        uom=None,
        evidence_span=(20, 24),
        fact_id="ATTRIBUTE:Material",
        official_label="Material",
        confidence_bp=9_000,
    )
    collapsed = extractor._deduplicate((first, duplicate))
    assert collapsed == (first,)
    conflicted = extractor._deduplicate((first, conflict))
    assert len(conflicted) == 2
    assert all(item.review_required for item in conflicted)
