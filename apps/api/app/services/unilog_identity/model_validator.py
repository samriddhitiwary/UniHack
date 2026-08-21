"""Validate optional model identity proposals without promoting final fields."""

import json

from app.domain.unilog_identity import (
    IdentityEvidenceSource,
    UnilogBrandCandidate,
    UnilogIdentityModelProposal,
)
from app.services.unilog_identity.normalization import normalize_identity
from app.services.unilog_identity.vocabulary_store import load_default_identity_artifact


def validate_model_brand_candidate(description: str, response: str) -> UnilogBrandCandidate | None:
    try:
        payload = json.loads(response)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict) or set(payload) != {"brandCandidate", "evidenceText"}:
        return None
    value, evidence = payload["brandCandidate"], payload["evidenceText"]
    if not isinstance(value, str) or not isinstance(evidence, str):
        return None
    start = description.find(evidence)
    if start < 0 or normalize_identity(value) != normalize_identity(evidence):
        return None
    artifact = load_default_identity_artifact()
    observed = {
        variant: item for item in artifact.observed_brands for variant in item.normalized_variants
    }
    item = observed.get(normalize_identity(value))
    if item is None or item.support_count < 2:
        return None
    return UnilogBrandCandidate(
        raw_value=value,
        normalized_value=item.canonical_observed_value,
        source_field=IdentityEvidenceSource.MODEL_ASSISTED,
        description_span=(start, start + len(evidence)),
        support_count=item.support_count,
        product_type_support=(),
        confidence_bp=min(6_500, item.confidence_bp),
        review_required=True,
    )


def validate_model_identity_proposal(
    description: str, response: str
) -> UnilogIdentityModelProposal | None:
    try:
        payload = json.loads(response)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict) or set(payload) != {
        "manufacturerCandidate",
        "brandCandidate",
        "evidenceText",
    }:
        return None
    manufacturer, brand, evidence = (
        payload["manufacturerCandidate"],
        payload["brandCandidate"],
        payload["evidenceText"],
    )
    if manufacturer is not None and not isinstance(manufacturer, str):
        return None
    if brand is not None and not isinstance(brand, str):
        return None
    if not isinstance(evidence, str) or (start := description.find(evidence)) < 0:
        return None
    artifact = load_default_identity_artifact()
    manufacturers = {
        variant: item
        for item in artifact.observed_manufacturers
        for variant in item.normalized_variants
    }
    if manufacturer is not None:
        item = manufacturers.get(normalize_identity(manufacturer))
        if (
            item is None
            or item.support_count < 2
            or normalize_identity(manufacturer) not in normalize_identity(evidence)
        ):
            return None
        manufacturer = item.canonical_observed_value
    brand_candidate = None
    if brand is not None:
        brands = {
            variant: item
            for item in artifact.observed_brands
            for variant in item.normalized_variants
        }
        brand_item = brands.get(normalize_identity(brand))
        if (
            brand_item is None
            or brand_item.support_count < 2
            or normalize_identity(brand) not in normalize_identity(evidence)
        ):
            return None
        brand_candidate = UnilogBrandCandidate(
            raw_value=brand,
            normalized_value=brand_item.canonical_observed_value,
            source_field=IdentityEvidenceSource.MODEL_ASSISTED,
            description_span=(start, start + len(evidence)),
            support_count=brand_item.support_count,
            product_type_support=(),
            confidence_bp=min(6_500, brand_item.confidence_bp),
            review_required=True,
        )
    if manufacturer is None and brand_candidate is None:
        return None
    return UnilogIdentityModelProposal(
        manufacturer_candidate=manufacturer,
        brand_candidate=brand_candidate,
        evidence_text=evidence,
        evidence_span=(start, start + len(evidence)),
    )
