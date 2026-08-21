"""Single-row enrichment, delivery assembly, provenance, and storage tests."""

from datetime import UTC, datetime

import pytest

from app.domain.unilog_challenge import (
    EvidenceSourceType,
    EvidenceStrength,
    FieldPopulationStrategy,
    FieldProvenance,
    FieldValidationStatus,
    UnilogFieldResolution,
)
from app.domain.unilog_challenge.delivery_schema import UNILOG_DELIVERY_HEADERS
from app.repositories.in_memory_unilog_enrichment import (
    InMemoryUnilogEnrichmentRepository,
)
from app.services.unilog_challenge.delivery_assembler import UnilogDeliveryRecordAssembler
from app.services.unilog_challenge.enrichment_service import UnilogEnrichmentService
from app.services.unilog_challenge.field_strategy import UnilogFieldPopulationStrategy
from tests.unit.unilog_challenge.helpers import challenge_row
from tests.unit.unilog_challenge.test_enrichment_extraction import vocabulary

_NOW = datetime(2026, 8, 21, 10, tzinfo=UTC)


def test_single_row_enrichment_produces_exact_schema_and_grounded_partial_record() -> None:
    row = challenge_row()
    result = UnilogEnrichmentService(now=lambda: _NOW).enrich_row(row, vocabulary())
    values = result.delivery_record.as_dict()
    assert tuple(values) == UNILOG_DELIVERY_HEADERS
    assert len(values) == 252
    assert values["Mfg_Part_Num"] == row.mfg_part_num
    assert values["MANUFACTURER_PART_NUMBER"] == row.mfg_part_num
    assert values["BRAND_NAME"] == "Diablo"
    assert values["MANUFACTURER_NAME"] == "Diablo Tools"
    assert values["Classpath"] is None
    assert values["Product Name"] == "Sanding Belt"
    assert values["WIDTH"] == "1/2" and values["WIDTH_UOM"] == "in"
    assert values["LENGTH"] == "18" and values["LENGTH_UOM"] == "in"
    assert values["UPC"] is None and values["UNSPSC"] is None
    assert values["Warranty"] is None and values["Product Image"] is None
    assert result.total_field_count == 252
    assert result.populated_field_count < 40
    assert result.created_at == _NOW


def test_supplier_ambiguity_keeps_manufacturer_blank_but_allows_partial_enrichment() -> None:
    row = challenge_row(
        description="3M 775L P150 Sanding Disc 50 Disc/Box",
        e1="3M",
        manufacturer="Jam Industrial Supply LLC (JAM01)",
    )
    result = UnilogEnrichmentService(now=lambda: _NOW).enrich_row(row, vocabulary())
    assert result.delivery_record.value("MANUFACTURER_NAME") is None
    assert result.delivery_record.value("BRAND_NAME") == "3M"
    assert result.delivery_record.value("Product Name") == "Sanding Disc"
    assert result.review_required
    assert "MANUFACTURER_REVIEW_REQUIRED" in result.warnings


def test_unknown_product_type_still_preserves_direct_fields_and_blanks_descriptions() -> None:
    row = challenge_row(description="ABC mysterious item", part="ABC")
    result = UnilogEnrichmentService(now=lambda: _NOW).enrich_row(row)
    assert result.delivery_record.value("Mfg_Part_Num") == "ABC"
    assert result.delivery_record.value("Product Name") is None
    assert result.delivery_record.value("Classpath") is None
    assert result.review_required


def test_enrichment_identity_is_policy_and_input_idempotent() -> None:
    service = UnilogEnrichmentService(now=lambda: _NOW)
    first = service.enrich_row(challenge_row(), vocabulary())
    second = service.enrich_row(challenge_row(), vocabulary())
    assert first.enrichment_id == second.enrichment_id
    assert first.policy_version == "unilog-enrichment-policy-v1"


def test_populated_resolutions_have_supported_provenance_and_confidence() -> None:
    result = UnilogEnrichmentService(now=lambda: _NOW).enrich_row(challenge_row(), vocabulary())
    populated = [item for item in result.field_resolutions if item.value is not None]
    assert populated
    assert all(item.provenance is not None for item in populated)
    assert all(item.confidence_bp > 0 for item in populated)
    assert all(
        item.provenance is not None
        and item.provenance.evidence_strength is not EvidenceStrength.UNSUPPORTED
        for item in populated
    )


def _resolution(field: str, value: str) -> UnilogFieldResolution:
    provenance = FieldProvenance(
        field_name=field,
        value=value,
        source_type=EvidenceSourceType.DETERMINISTIC_PARSE,
        source_reference="test",
        method="test",
        evidence_strength=EvidenceStrength.DERIVED,
        confidence_bp=9_000,
        review_required=False,
    )
    return UnilogFieldResolution(
        field_name=field,
        value=value,
        strategy=FieldPopulationStrategy.DETERMINISTIC_PARSE,
        validation_status=FieldValidationStatus.VALID,
        provenance=provenance,
        confidence_bp=9_000,
        review_required=False,
    )


def test_delivery_assembler_rejects_duplicate_unknown_and_invalid_attribute_fields() -> None:
    assembler = UnilogDeliveryRecordAssembler()
    with pytest.raises(ValueError, match="duplicate"):
        assembler.assemble((_resolution("Product Name", "Valve"),) * 2)
    invalid = UnilogFieldResolution(
        field_name="Internal Confidence",
        value=None,
        strategy=FieldPopulationStrategy.UNSUPPORTED,
        validation_status=FieldValidationStatus.UNSUPPORTED,
        provenance=None,
        confidence_bp=0,
        review_required=False,
    )
    with pytest.raises(ValueError, match="outside delivery schema"):
        assembler.assemble((invalid,))
    with pytest.raises(ValueError, match="ATTRIBUTE"):
        assembler.assemble((_resolution("ATTRIBUTE_LABEL 1", "Material"),))


def test_result_repository_is_separate_and_idempotent() -> None:
    result = UnilogEnrichmentService(now=lambda: _NOW).enrich_row(challenge_row(), vocabulary())
    repository = InMemoryUnilogEnrichmentRepository()
    repository.save(result)
    repository.save(result)
    assert repository.get(result.enrichment_id) == result
    assert repository.get("missing") is None


def test_population_strategy_covers_every_exact_header_once() -> None:
    strategy = UnilogFieldPopulationStrategy()
    entries = strategy.entries()
    assert len(entries) == 252
    assert tuple(item.field for item in entries) == UNILOG_DELIVERY_HEADERS
    assert all(
        item.possible_source
        and item.validation
        and item.confidence_behavior
        and item.blank_behavior
        for item in entries
    )
    with pytest.raises(KeyError):
        strategy.for_field("Internal Confidence")
