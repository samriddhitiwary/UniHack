"""Exact schema, bounded mapping, provenance, and comparison tests."""

from decimal import Decimal

import pytest

from app.domain.unilog_challenge import (
    ComparisonStatus,
    EvidenceSourceType,
    EvidenceStrength,
    FieldProvenance,
    SourceReferences,
    UnilogAttributeCandidate,
    UnilogDeliveryRecord,
)
from app.domain.unilog_challenge.delivery_schema import UNILOG_DELIVERY_HEADERS
from app.services.unilog_challenge.delivery_mapping import (
    map_attribute_candidates,
    map_item_features,
    map_source_references,
)
from app.services.unilog_challenge.ground_truth import compare_field
from app.services.unilog_challenge.policy import require_supported_provenance


def test_exact_delivery_schema_has_252_unique_official_headers() -> None:
    assert len(UNILOG_DELIVERY_HEADERS) == 252
    assert len(set(UNILOG_DELIVERY_HEADERS)) == 252
    assert UNILOG_DELIVERY_HEADERS[:7] == (
        "MFR URL",
        "Ref URL 1",
        "Ref URL 2",
        "Ref URL 3",
        "Ref URL 4",
        "Ref URL 5",
        "PART_NUMBER",
    )
    assert UNILOG_DELIVERY_HEADERS[-1] == "Actual Image (Yes/No)"


def test_blank_delivery_record_preserves_all_headers_and_blanks() -> None:
    record = UnilogDeliveryRecord.blank()
    assert tuple(record.as_dict()) == UNILOG_DELIVERY_HEADERS
    assert all(value is None for value in record.as_dict().values())


def test_delivery_record_rejects_unknown_missing_or_reordered_fields() -> None:
    with pytest.raises(ValueError, match="exact ordered schema"):
        UnilogDeliveryRecord.from_mapping({"MFR URL": None, "Internal Notes": "bad"})
    reordered = {header: None for header in reversed(UNILOG_DELIVERY_HEADERS)}
    with pytest.raises(ValueError, match="exact ordered schema"):
        UnilogDeliveryRecord.from_mapping(reordered)


def test_attribute_mapping_uses_exact_triple_headers() -> None:
    candidate = UnilogAttributeCandidate(
        label="Voltage Rating",
        raw_value="120",
        normalized_value=None,
        uom="V",
        source=EvidenceSourceType.RAW_INPUT,
        confidence_bp=10_000,
        review_required=False,
    )
    assert map_attribute_candidates([candidate]) == {
        "ATTRIBUTE_LABEL 1": "Voltage Rating",
        "ATTRIBUTE_VALUE 1": "120",
        "ATTRIBUTE_UOM 1": "V",
    }
    with pytest.raises(ValueError, match="50"):
        map_attribute_candidates([candidate] * 51)


def test_features_and_reference_urls_are_bounded() -> None:
    assert map_item_features(["One", "Two"]) == {
        "ITEM_FEATURES_1": "One",
        "ITEM_FEATURES_2": "Two",
    }
    with pytest.raises(ValueError, match="20"):
        map_item_features([str(index) for index in range(21)])
    refs = SourceReferences(
        manufacturer_url="https://manufacturer.example/item",
        reference_urls=("https://manufacturer.example/spec",),
    )
    assert map_source_references(refs) == {
        "MFR URL": "https://manufacturer.example/item",
        "Ref URL 1": "https://manufacturer.example/spec",
    }
    with pytest.raises(ValueError, match="five"):
        SourceReferences(manufacturer_url=None, reference_urls=("x",) * 6)


def test_provenance_validates_field_and_basis_points() -> None:
    provenance = FieldProvenance(
        field_name="MANUFACTURER_NAME",
        value="Acme LLC",
        source_type=EvidenceSourceType.DETERMINISTIC_PARSE,
        source_reference="Part_Manuf",
        method="final-parenthesis-parser-v1",
        evidence_strength=EvidenceStrength.DERIVED,
        confidence_bp=8_000,
        review_required=True,
    )
    require_supported_provenance(provenance)
    with pytest.raises(ValueError, match="delivery schema"):
        FieldProvenance(
            field_name="AI Confidence",
            value=Decimal("1"),
            source_type=EvidenceSourceType.RAW_INPUT,
            source_reference="input",
            method="direct",
            evidence_strength=EvidenceStrength.DIRECT,
            confidence_bp=10_000,
            review_required=False,
        )


def test_non_hallucination_policy_rejects_unsupported_and_unguarded_model_values() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        require_supported_provenance(
            FieldProvenance(
                field_name="UPC",
                value="invented",
                source_type=EvidenceSourceType.RAW_INPUT,
                source_reference="none",
                method="guess",
                evidence_strength=EvidenceStrength.UNSUPPORTED,
                confidence_bp=0,
                review_required=True,
            )
        )
    with pytest.raises(ValueError, match="model inference"):
        require_supported_provenance(
            FieldProvenance(
                field_name="Classpath",
                value="unsupported",
                source_type=EvidenceSourceType.VALIDATED_MODEL_INFERENCE,
                source_reference="model",
                method="classifier",
                evidence_strength=EvidenceStrength.INFERRED,
                confidence_bp=8_000,
                review_required=False,
            )
        )


@pytest.mark.parametrize(
    ("expected", "actual", "status"),
    [
        ("Acme", "Acme", ComparisonStatus.EXACT_MATCH),
        (" Acme  LLC ", "acme llc", ComparisonStatus.NORMALIZED_MATCH),
        ("Acme", "Other", ComparisonStatus.MISMATCH),
        (None, "Acme", ComparisonStatus.EXPECTED_BLANK),
        ("Acme", None, ComparisonStatus.ACTUAL_BLANK),
        (None, None, ComparisonStatus.BOTH_BLANK),
    ],
)
def test_field_comparison_states(
    expected: str | None, actual: str | None, status: ComparisonStatus
) -> None:
    assert compare_field("BRAND_NAME", expected, actual).status is status
