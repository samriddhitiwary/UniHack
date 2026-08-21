from pathlib import Path

from app.domain.unilog_challenge import (
    ManufacturerParseStatus,
    ResolutionStatus,
    UnilogChallengeInputRow,
)
from app.domain.unilog_identity import IdentityReviewReason
from app.services.unilog_challenge.cleansing import clean_challenge_value
from app.services.unilog_challenge.manufacturer import parse_part_manufacturer
from app.services.unilog_identity.model_validator import (
    validate_model_brand_candidate,
    validate_model_identity_proposal,
)
from app.services.unilog_identity.resolver import UnilogIdentityResolver
from app.services.unilog_identity.supplier_classifier import SupplierEvidenceClassifier
from app.services.unilog_identity.vocabulary_builder import build_manufacturer_brand_evidence
from app.services.unilog_identity.vocabulary_store import (
    DEFAULT_IDENTITY_ARTIFACT_PATH,
    load_identity_artifact,
    write_identity_artifact,
)


def row(
    *,
    mpn: str = "TEST-1",
    description: str = "Generic accessory",
    manufacturer: str = "-",
    e1: str = "-- Unbranded --",
    unilog: str = "-- No Unilog Brand --",
    dib: str = "-- No DIB Brand --",
) -> UnilogChallengeInputRow:
    parsed = parse_part_manufacturer(manufacturer)
    return UnilogChallengeInputRow(
        row_id="a" * 64,
        source_row_number=2,
        mfg_part_num=mpn,
        part_desc=description,
        e1_brand_raw=e1,
        unilog_brand_raw=unilog,
        dib_brand_raw=dib,
        part_manuf_raw=manufacturer,
        e1_brand_clean=clean_challenge_value(e1),
        unilog_brand_clean=clean_challenge_value(unilog),
        dib_brand_clean=clean_challenge_value(dib),
        parsed_manufacturer=parsed.manufacturer_text,
        source_reference_code=parsed.source_reference_code,
        manufacturer_parse_status=parsed.status,
    )


def test_supplier_tokens_are_negative_role_evidence_not_manufacturer_truth() -> None:
    evidence = SupplierEvidenceClassifier().classify(
        "Jam Industrial Supply LLC (JAMIN)", support_count=6
    )
    assert evidence is not None
    assert evidence.supplier_likelihood_bp == 9_000
    result = UnilogIdentityResolver().resolve(
        row(
            mpn="3MABR-7100075678",
            description="3M 775L Stikit Film P150 - Cubitron II 50 Disc/Box",
            manufacturer="Jam Industrial Supply LLC (JAMIN)",
        )
    )
    assert result.manufacturer is None
    assert result.supplier_organization == "Jam Industrial Supply LLC"
    assert result.brand == "3M"
    assert IdentityReviewReason.SUPPLIER_ONLY_EVIDENCE in result.review_reasons


def test_repeated_relationship_can_support_manufacturer_and_brand_independently() -> None:
    resolver = UnilogIdentityResolver()
    assert "freud inc" in {
        manufacturer for manufacturer, _ in resolver.index.brand_manufacturers["diablo"]
    }
    freud = resolver.resolve(
        row(
            description="Diablo 7-1/4 in saw blade",
            manufacturer="Freud Inc (2435)",
            dib="Diablo",
        )
    )
    assert freud.manufacturer == "Freud Inc"
    assert freud.brand == "Diablo"
    assert freud.manufacturer_status is ResolutionStatus.RESOLVED
    philips = resolver.resolve(row(description="LED lamp", manufacturer="Phillips Lighting (5831)"))
    assert philips.brand == "Philips"
    assert philips.manufacturer == "Phillips Lighting"


def test_brand_fields_conflict_without_majority_vote() -> None:
    result = UnilogIdentityResolver().resolve(row(e1="TREX", dib="DEWALT"))
    assert result.brand is None
    assert result.brand_status is ResolutionStatus.AMBIGUOUS
    assert IdentityReviewReason.BRAND_FIELD_CONFLICT in result.review_reasons


def test_single_row_or_unknown_prefix_cannot_promote_brand() -> None:
    result = UnilogIdentityResolver().resolve(row(mpn="UNSEEN-100", description="Unseen accessory"))
    assert result.brand is None
    assert result.brand_status is ResolutionStatus.NOT_FOUND


def test_placeholders_remain_missing_and_brand_only_is_supported() -> None:
    missing = UnilogIdentityResolver().resolve(row())
    assert missing.brand is None
    assert missing.manufacturer is None
    brand_only = UnilogIdentityResolver().resolve(
        row(description="3M abrasive film", mpn="3MABR-0000000000")
    )
    assert brand_only.brand == "3M"
    assert brand_only.manufacturer is None


def test_model_candidate_requires_exact_evidence_and_observed_vocabulary() -> None:
    accepted = validate_model_brand_candidate(
        "Diablo saw blade", '{"brandCandidate":"Diablo","evidenceText":"Diablo"}'
    )
    assert accepted is not None
    assert accepted.review_required is True
    assert (
        validate_model_brand_candidate(
            "saw blade", '{"brandCandidate":"Diablo","evidenceText":"Diablo"}'
        )
        is None
    )
    assert (
        validate_model_brand_candidate(
            "Invented saw", '{"brandCandidate":"Invented","evidenceText":"Invented"}'
        )
        is None
    )


def test_model_identity_proposal_is_review_only_and_rejects_hallucination() -> None:
    accepted = validate_model_identity_proposal(
        "Freud Inc makes Diablo saw blades",
        '{"manufacturerCandidate":"Freud Inc","brandCandidate":"Diablo",'
        '"evidenceText":"Freud Inc makes Diablo"}',
    )
    assert accepted is not None
    assert accepted.manufacturer_candidate == "Freud Inc"
    assert accepted.brand_candidate is not None
    assert accepted.brand_candidate.normalized_value == "Diablo"
    assert accepted.review_required is True
    assert (
        validate_model_identity_proposal(
            "Invented makes Diablo saw blades",
            '{"manufacturerCandidate":"Invented","brandCandidate":"Diablo",'
            '"evidenceText":"Invented makes Diablo"}',
        )
        is None
    )


def test_product_type_can_reject_but_never_invent_brand() -> None:
    resolver = UnilogIdentityResolver()
    candidate = resolver.resolve(
        row(description="3M abrasive film", mpn="UNSEEN-100"), product_type="3M"
    )
    assert candidate.brand is None


def test_artifact_round_trip_preserves_hash_and_indexes(tmp_path: Path) -> None:
    artifact = load_identity_artifact(DEFAULT_IDENTITY_ARTIFACT_PATH)
    target = tmp_path / "identity.json"
    write_identity_artifact(artifact, target)
    restored = load_identity_artifact(target)
    assert restored == artifact
    assert artifact.statistics.input_rows == 1_000
    assert artifact.statistics.unique_organizations == 75
    assert artifact.statistics.supplier_like_organizations == 5
    assert len(artifact.artifact_hash) == 64


def test_evidence_builder_is_deterministic_and_separates_supplier_relations() -> None:
    rows = tuple(
        row(
            mpn=f"DB-{index}",
            description="Diablo saw blade",
            manufacturer="Freud Inc (2435)",
            dib="Diablo",
        )
        for index in range(3)
    ) + tuple(
        row(
            mpn=f"AB-{index}",
            description="3M abrasive film",
            manufacturer="Jam Industrial Supply LLC (JAMIN)",
            e1="3M",
        )
        for index in range(3)
    )
    first = build_manufacturer_brand_evidence(
        rows, input_sha256="a" * 64, ground_truth_sha256="b" * 64
    )
    second = build_manufacturer_brand_evidence(
        rows, input_sha256="a" * 64, ground_truth_sha256="b" * 64
    )
    assert first == second
    assert first.artifact_hash == second.artifact_hash
    assert first.statistics.input_rows == 6
    assert first.statistics.supplier_like_organizations == 1
    assert first.statistics.description_brand_candidates == 2
    assert len(first.manufacturer_brand_relations) == 1
    assert len(first.supplier_brand_relations) == 1


def test_no_row_specific_expected_identity_lookup_exists() -> None:
    source = Path(__file__).parents[3] / "app" / "services" / "unilog_identity" / "resolver.py"
    content = source.read_text(encoding="utf-8")
    assert "PDSH4816AF" not in content
    assert "WDTS7024RZ" not in content
    assert "3MABR" not in content
    assert ManufacturerParseStatus.PARSED.value not in content
