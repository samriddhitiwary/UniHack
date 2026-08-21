"""Atomic persistence and cached indexed access for identity evidence."""

import json
from dataclasses import asdict
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.domain.unilog_identity import (
    IdentityEvidenceSource,
    IdentityRelationEvidence,
    LeadingDescriptionPhraseEvidence,
    ObservedIdentityVocabularyEntry,
    ObservedMpnPrefixEvidence,
    UnilogIdentityVocabularyStatistics,
    UnilogManufacturerBrandEvidenceArtifact,
    UnilogOrganizationEvidence,
)

DEFAULT_IDENTITY_ARTIFACT_PATH = (
    Path(__file__).parents[2] / "reference_data" / "unilog_manufacturer_brand_v1.json"
)


def write_identity_artifact(value: UnilogManufacturerBrandEvidenceArtifact, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(_jsonable(asdict(value)), indent=2, sort_keys=True), encoding="utf-8"
    )
    temporary.replace(path)


def load_identity_artifact(path: Path) -> UnilogManufacturerBrandEvidenceArtifact:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return UnilogManufacturerBrandEvidenceArtifact(
        policy_version=payload["policy_version"],
        input_sha256=payload["input_sha256"],
        ground_truth_sha256=payload["ground_truth_sha256"],
        artifact_hash=payload["artifact_hash"],
        organizations=tuple(_organization(item) for item in payload["organizations"]),
        observed_manufacturers=tuple(
            _vocabulary(item) for item in payload["observed_manufacturers"]
        ),
        observed_brands=tuple(_vocabulary(item) for item in payload["observed_brands"]),
        leading_description_tokens=tuple(
            LeadingDescriptionPhraseEvidence(**item)
            for item in payload["leading_description_tokens"]
        ),
        mpn_prefix_evidence=tuple(
            ObservedMpnPrefixEvidence(**item) for item in payload["mpn_prefix_evidence"]
        ),
        manufacturer_brand_relations=tuple(
            IdentityRelationEvidence(**item) for item in payload["manufacturer_brand_relations"]
        ),
        supplier_brand_relations=tuple(
            IdentityRelationEvidence(**item) for item in payload["supplier_brand_relations"]
        ),
        statistics=UnilogIdentityVocabularyStatistics(**payload["statistics"]),
    )


def _organization(item: dict[str, Any]) -> UnilogOrganizationEvidence:
    return UnilogOrganizationEvidence(
        raw_value=item["raw_value"],
        clean_value=item["clean_value"],
        parsed_name=item["parsed_name"],
        source_reference_code=item["source_reference_code"],
        source_field=IdentityEvidenceSource(item["source_field"]),
        supplier_likelihood_bp=item["supplier_likelihood_bp"],
        manufacturer_likelihood_bp=item["manufacturer_likelihood_bp"],
        evidence_reasons=tuple(item["evidence_reasons"]),
        support_count=item["support_count"],
        example_rows=tuple(item["example_rows"]),
    )


def _vocabulary(item: dict[str, Any]) -> ObservedIdentityVocabularyEntry:
    return ObservedIdentityVocabularyEntry(
        canonical_observed_value=item["canonical_observed_value"],
        normalized_variants=tuple(item["normalized_variants"]),
        support_count=item["support_count"],
        source_fields=tuple(IdentityEvidenceSource(value) for value in item["source_fields"]),
        example_rows=tuple(item["example_rows"]),
        confidence_bp=item["confidence_bp"],
    )


@lru_cache(maxsize=1)
def load_default_identity_artifact() -> UnilogManufacturerBrandEvidenceArtifact:
    return load_identity_artifact(DEFAULT_IDENTITY_ARTIFACT_PATH)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value
