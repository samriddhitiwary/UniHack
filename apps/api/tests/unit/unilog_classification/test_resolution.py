"""Dataset vocabulary, resolver, model boundary, and verified mapping tests."""

from dataclasses import replace

from app.domain.unilog_classification import (
    ClassificationReviewReason,
    ProductTypeMatchMethod,
)
from app.services.unilog_classification.classpath_resolver import UnilogClasspathResolver
from app.services.unilog_classification.model_validator import validate_model_product_type_proposal
from app.services.unilog_classification.product_type_resolver import UnilogProductTypeResolver
from app.services.unilog_classification.vocabulary_builder import (
    build_classification_vocabulary,
    normalize_product_phrase,
)
from app.services.unilog_classification.vocabulary_store import (
    load_default_classification_vocabulary,
)
from tests.unit.unilog_challenge.helpers import challenge_row


def test_representative_sanding_belt_and_stikit_film_retain_exact_evidence() -> None:
    resolver = UnilogProductTypeResolver()
    belt = resolver.resolve('DCB518ASTS06G Diablo 1/2"x18" - Sanding Belt 6pc')
    film = resolver.resolve("3M 775L Stikit Film P150 - Cubitron II 50 Disc/Box")
    assert (belt.product_type, belt.evidence_text) == ("Sanding Belt", "Sanding Belt")
    assert (film.product_type, film.evidence_text) == ("Stikit Film", "Stikit Film")
    assert belt.evidence_span is not None


def test_safe_normalization_preserves_semantic_product_specificity() -> None:
    assert normalize_product_phrase("  CUT-OFF   Disc ") == "cut off disc"
    resolver = UnilogProductTypeResolver()
    assert resolver.resolve("18V Circular Saw").product_type == "Circular Saw"
    assert resolver.resolve("10in Saw Blade").product_type == "Saw Blade"


def test_verified_observed_abbreviation_has_distinct_method() -> None:
    result = UnilogProductTypeResolver().resolve("Bronze outdoor wall lt")
    assert result.product_type == "Wall Light"
    assert result.match_method is ProductTypeMatchMethod.OBSERVED_ABBREVIATION


def test_generic_only_and_unknown_descriptions_require_review() -> None:
    resolver = UnilogProductTypeResolver()
    generic = resolver.resolve("Replacement Kit")
    unknown = resolver.resolve("ZXQ unheard noun")
    assert generic.review_reasons == (ClassificationReviewReason.PRODUCT_TYPE_GENERIC,)
    assert unknown.review_reasons == (ClassificationReviewReason.PRODUCT_TYPE_UNKNOWN,)


def test_equal_observed_variant_collision_is_ambiguous() -> None:
    vocabulary = load_default_classification_vocabulary()
    first = replace(
        vocabulary.entries[0],
        canonical_product_type="Alpha Widget",
        normalized_key="alpha widget",
        variants=("shared widget",),
    )
    second = replace(
        vocabulary.entries[1],
        canonical_product_type="Beta Widget",
        normalized_key="beta widget",
        variants=("shared widget",),
    )
    custom = replace(
        vocabulary,
        entries=(first, second),
        abbreviations=(),
        verified_classpath_mappings=(),
    )
    result = UnilogProductTypeResolver(custom).resolve("a shared widget")
    assert result.match_method is ProductTypeMatchMethod.AMBIGUOUS
    assert result.candidate_product_types == ("Alpha Widget", "Beta Widget")


def test_model_proposal_requires_exact_evidence_and_rejects_specificity() -> None:
    accepted = validate_model_product_type_proposal(
        "Compact Sanding Belt", '{"productType":"Sanding Belt","evidenceText":"Sanding Belt"}'
    )
    assert accepted is not None and accepted.match_method is ProductTypeMatchMethod.MODEL_ASSISTED
    assert (
        validate_model_product_type_proposal(
            "Valve", '{"productType":"Premium Aerospace Valve","evidenceText":"Valve"}'
        )
        is None
    )
    assert validate_model_product_type_proposal("Valve", "not-json") is None


def test_official_mapping_generalizes_by_type_but_rejects_model_only_type() -> None:
    resolver = UnilogProductTypeResolver()
    classpaths = UnilogClasspathResolver()
    deterministic = resolver.resolve("A quiet built-in Dishwasher")
    mapped = classpaths.resolve(deterministic)
    assert mapped.classpath == (
        "Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers"
    )
    model = validate_model_product_type_proposal(
        "Dishwasher", '{"productType":"Dishwasher","evidenceText":"Dishwasher"}'
    )
    assert model is not None
    rejected = classpaths.resolve(model)
    assert rejected.classpath is None
    assert rejected.confidence_bp == 0


def test_builder_counts_duplicate_rows_and_is_deterministic() -> None:
    row = challenge_row(description="ACME Sanding Belt")
    duplicate = replace(row, row_id="b" * 64, source_row_number=3)
    first = build_classification_vocabulary((row, duplicate), input_sha256="a" * 64)
    second = build_classification_vocabulary((row, duplicate), input_sha256="a" * 64)
    sanding = next(item for item in first.entries if item.canonical_product_type == "Sanding Belt")
    assert sanding.occurrence_count == 2
    assert first.vocabulary_hash == second.vocabulary_hash
    assert len(sanding.example_evidence) == 1
