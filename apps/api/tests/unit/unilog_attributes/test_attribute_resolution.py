"""Extraction, normalization, mapping, conflict, model, and delivery tests."""

from dataclasses import replace

from app.domain.unilog_attributes import AttributeReviewReason
from app.domain.unilog_challenge import UNILOG_DELIVERY_HEADERS
from app.services.unilog_attributes.attribute_conflict_resolver import (
    resolve_attribute_conflicts,
)
from app.services.unilog_attributes.model_validator import validate_model_attribute_candidates
from app.services.unilog_attributes.unit_normalizer import normalize_observed_uom
from app.services.unilog_attributes.vocabulary_store import (
    load_attribute_vocabulary,
    load_default_attribute_vocabulary,
    write_attribute_vocabulary,
)
from app.services.unilog_challenge.attribute_extractor import UnilogAttributeExtractor
from app.services.unilog_challenge.description_signal_extractor import (
    UnilogDescriptionSignalExtractor,
)
from app.services.unilog_challenge.enrichment_service import UnilogEnrichmentService
from app.services.unilog_challenge.measurement_parser import (
    parse_measurements,
    parse_trade_fraction,
)
from tests.unit.unilog_challenge.helpers import challenge_row


def _extract(description: str):
    signals = UnilogDescriptionSignalExtractor().extract(challenge_row(description=description))
    return UnilogAttributeExtractor().extract(signals, None)


def test_sanding_belt_uses_type_context_for_dimensions_and_quantity() -> None:
    items = _extract('DCB518ASTS06G Diablo 1/2"x18" - Sanding Belt 6pc')
    by_name = {item.semantic_name: item for item in items}
    assert by_name["Width"].normalized_value == "1/2"
    assert by_name["Length"].normalized_value == "18"
    assert by_name["Package Quantity"].normalized_value == "6"
    assert by_name["Dimensions"].official_label == "Size"
    assert by_name["Width"].uom == by_name["Length"].uom == "in"


def test_stikit_grit_and_box_quantity_are_contextual_semantic_candidates() -> None:
    items = _extract("3M 775L Stikit Film P150 - Cubitron II 50 Disc/Box")
    by_name = {item.semantic_name: item for item in items}
    assert by_name["Grit"].normalized_value == "P150"
    assert by_name["Package Quantity"].normalized_value == "50"
    assert by_name["Package Unit"].normalized_value.casefold() == "disc/box"
    assert by_name["Grit"].official_label is None


def test_exact_fractions_multi_dimensions_and_unknown_orientation() -> None:
    assert str(parse_trade_fraction("1-1/4")) == "5/4"
    measurements = parse_measurements("Panel 24 x 24-1/4 in")
    assert tuple(item.exact_value for item in measurements) == ("24", "24-1/4")
    items = _extract("Unknown Panel 24 x 24-1/4 in")
    names = {item.semantic_name for item in items}
    assert "Width" not in names and "Length" not in names
    assert {"Dimension 1", "Dimension 2", "Dimensions"} <= names


def test_observed_unit_normalization_is_small_and_case_safe() -> None:
    assert normalize_observed_uom('"') == "in"
    assert normalize_observed_uom("inches") == "in"
    assert normalize_observed_uom("v") == "V"
    assert normalize_observed_uom("unknown") is None


def test_electrical_material_and_unknown_labels_are_evidence_bound() -> None:
    items = _extract("Steel controller 120 V 15A 3/4 HP")
    by_name = {item.semantic_name: item for item in items}
    assert by_name["Material"].official_label == "Material"
    assert by_name["Voltage Rating"].official_label == "Voltage Rating"
    assert by_name["Amperage Rating"].official_label == "Amperage Rating"
    assert by_name["Horsepower"].official_label is None
    assert AttributeReviewReason.ATTRIBUTE_LABEL_UNKNOWN in by_name["Horsepower"].review_reasons


def test_duplicates_collapse_and_conflicting_values_are_not_selected() -> None:
    items = _extract("Steel and Steel")
    assert len([item for item in items if item.semantic_name == "Material"]) == 1
    signals = UnilogDescriptionSignalExtractor().extract(
        challenge_row(description="Steel and Copper")
    )
    raw = UnilogAttributeExtractor()._materials(signals)
    conflicts = resolve_attribute_conflicts(raw)
    assert len(conflicts) == 2
    assert all(item.review_required for item in conflicts)
    assert all(
        AttributeReviewReason.ATTRIBUTE_CONFLICT in item.review_reasons for item in conflicts
    )


def test_model_candidates_require_source_values_and_cannot_invent_official_labels() -> None:
    accepted = validate_model_attribute_candidates(
        "Rated 120 V",
        '{"attributes":[{"semanticName":"Voltage Rating","value":"120",'
        '"uom":"V","evidenceText":"120 V"}]}',
    )
    assert len(accepted) == 1 and accepted[0].official_label == "Voltage Rating"
    rejected = validate_model_attribute_candidates(
        "No rating supplied",
        '{"attributes":[{"semanticName":"Voltage Rating","value":"120",'
        '"uom":"V","evidenceText":"120 V"}]}',
    )
    assert rejected == ()
    unknown = validate_model_attribute_candidates(
        "3/4 HP",
        '{"attributes":[{"semanticName":"Horsepower","value":"3/4",'
        '"uom":"HP","evidenceText":"3/4 HP"}]}',
    )
    assert unknown and unknown[0].official_label is None


def test_attribute_artifact_round_trips_and_reports_official_evidence(tmp_path) -> None:
    vocabulary = load_default_attribute_vocabulary()
    path = tmp_path / "attributes.json"
    write_attribute_vocabulary(vocabulary, path)
    loaded = load_attribute_vocabulary(path)
    assert loaded == vocabulary
    assert loaded.statistics.input_rows == 1_000
    assert loaded.statistics.observed_labels == 15
    assert loaded.statistics.observed_uoms == 4


def test_dishwasher_material_uses_observed_slot_without_mpn_lookup() -> None:
    first = challenge_row(part="ONE", description="ONE Dishwasher SS - Display Only")
    second = replace(first, row_id="b" * 64, mfg_part_num="TWO", source_row_number=3)
    one = UnilogEnrichmentService().enrich_row(first)
    two = UnilogEnrichmentService().enrich_row(second)
    for result in (one, two):
        assert result.delivery_record.value("ATTRIBUTE_LABEL 13") == "Material"
        assert result.delivery_record.value("ATTRIBUTE_VALUE 13") == "Stainless Steel"
        assert result.delivery_record.value("ATTRIBUTE_LABEL 1") is None
        assert tuple(result.delivery_record.as_dict()) == UNILOG_DELIVERY_HEADERS
