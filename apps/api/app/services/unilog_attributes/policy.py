"""Verified semantic-label and evidence-backed UOM normalization policies."""

from app.domain.unilog_attributes import (
    AttributeVocabularySource,
    SemanticAttributeToObservedLabelMapping,
    UnilogObservedUomResolution,
)

SEMANTIC_LABEL_MAPPINGS = (
    SemanticAttributeToObservedLabelMapping(
        semantic_name="Amperage Rating",
        observed_label="Amperage Rating",
        source=AttributeVocabularySource.OBSERVED_LABELLED_OUTPUT,
        confidence_bp=9_500,
    ),
    SemanticAttributeToObservedLabelMapping(
        semantic_name="Dimensions",
        observed_label="Size",
        source=AttributeVocabularySource.HUMAN_APPROVED,
        confidence_bp=9_000,
    ),
    SemanticAttributeToObservedLabelMapping(
        semantic_name="Material",
        observed_label="Material",
        source=AttributeVocabularySource.OBSERVED_LABELLED_OUTPUT,
        confidence_bp=9_500,
    ),
    SemanticAttributeToObservedLabelMapping(
        semantic_name="Series",
        observed_label="Series",
        source=AttributeVocabularySource.OBSERVED_LABELLED_OUTPUT,
        confidence_bp=9_500,
    ),
    SemanticAttributeToObservedLabelMapping(
        semantic_name="Sound Level",
        observed_label="Sound Level",
        source=AttributeVocabularySource.OBSERVED_LABELLED_OUTPUT,
        confidence_bp=9_500,
    ),
    SemanticAttributeToObservedLabelMapping(
        semantic_name="Voltage Rating",
        observed_label="Voltage Rating",
        source=AttributeVocabularySource.OBSERVED_LABELLED_OUTPUT,
        confidence_bp=9_500,
    ),
)


def _uom(raw: str, normalized: str, confidence: int = 9_500) -> UnilogObservedUomResolution:
    return UnilogObservedUomResolution(
        raw_uom=raw,
        normalized_uom=normalized,
        source=AttributeVocabularySource.HUMAN_APPROVED,
        confidence_bp=confidence,
        review_required=False,
    )


UOM_NORMALIZATION_MAPPINGS = (
    _uom('"', "in"),
    _uom("in", "in"),
    _uom("in.", "in"),
    _uom("inch", "in"),
    _uom("inches", "in"),
    _uom("V", "V"),
    _uom("A", "A"),
    _uom("dBA", "dBA"),
    _uom("ft", "ft"),
    _uom("mm", "mm"),
    _uom("psi", "psi"),
    _uom("HP", "HP"),
    _uom("Hz", "Hz"),
)
