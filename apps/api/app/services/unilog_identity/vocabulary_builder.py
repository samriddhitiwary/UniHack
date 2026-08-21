"""Build deterministic dataset-derived manufacturer and brand evidence."""

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from enum import Enum

from app.domain.unilog_challenge import UnilogChallengeInputRow, UnilogGroundTruthRecord
from app.domain.unilog_identity import (
    UNILOG_IDENTITY_POLICY_VERSION,
    IdentityEvidenceSource,
    IdentityRelationEvidence,
    LeadingDescriptionPhraseEvidence,
    ObservedIdentityVocabularyEntry,
    ObservedMpnPrefixEvidence,
    UnilogIdentityVocabularyStatistics,
    UnilogManufacturerBrandEvidenceArtifact,
)
from app.services.unilog_classification.vocabulary_builder import matched_rule
from app.services.unilog_identity.normalization import (
    leading_phrase,
    mpn_prefix,
    normalize_identity,
)
from app.services.unilog_identity.supplier_classifier import SupplierEvidenceClassifier


def _brand_values(row: UnilogChallengeInputRow) -> tuple[tuple[str, IdentityEvidenceSource], ...]:
    return tuple(
        (value, source)
        for value, source in (
            (row.e1_brand_clean, IdentityEvidenceSource.E1_BRAND),
            (row.unilog_brand_clean, IdentityEvidenceSource.UNILOG_BRAND),
            (row.dib_brand_clean, IdentityEvidenceSource.DIB_BRAND),
        )
        if value is not None
    )


def build_manufacturer_brand_evidence(
    rows: tuple[UnilogChallengeInputRow, ...],
    *,
    input_sha256: str,
    ground_truth_sha256: str,
    ground_truth_rows: tuple[UnilogGroundTruthRecord, ...] = (),
) -> UnilogManufacturerBrandEvidenceArtifact:
    classifier = SupplierEvidenceClassifier()
    organization_rows: dict[str, list[UnilogChallengeInputRow]] = defaultdict(list)
    brands: dict[str, list[tuple[str, IdentityEvidenceSource, str]]] = defaultdict(list)
    for row in rows:
        if row.parsed_manufacturer and row.parsed_manufacturer.strip(" -"):
            organization_rows[normalize_identity(row.parsed_manufacturer)].append(row)
        for value, source in _brand_values(row):
            brands[normalize_identity(value)].append((value, source, row.row_id))

    official_manufacturers: list[tuple[str, str]] = []
    official_brands: list[tuple[str, str]] = []
    for truth in ground_truth_rows:
        manufacturer = truth.expected.value("MANUFACTURER_NAME")
        brand = truth.expected.value("BRAND_NAME")
        if isinstance(manufacturer, str) and manufacturer:
            official_manufacturers.append((manufacturer, "official-labelled-output"))
        if isinstance(brand, str) and brand:
            official_brands.append((brand, "official-labelled-output"))

    organizations = []
    for key in sorted(organization_rows):
        grouped = organization_rows[key]
        evidence = classifier.classify(
            grouped[0].part_manuf_raw,
            support_count=len(grouped),
            example_rows=tuple(row.row_id for row in grouped[:5]),
        )
        if evidence:
            organizations.append(evidence)

    observed_brands = _vocabulary_entries(brands, official_brands)
    brand_by_key = {
        normalize_identity(item.canonical_observed_value): item for item in observed_brands
    }
    observed_manufacturers = []
    for item in organizations:
        if item.support_count >= 2 and item.manufacturer_likelihood_bp >= 6_500:
            observed_manufacturers.append(
                ObservedIdentityVocabularyEntry(
                    canonical_observed_value=item.parsed_name,
                    normalized_variants=(normalize_identity(item.parsed_name),),
                    support_count=item.support_count,
                    source_fields=(IdentityEvidenceSource.PART_MANUF,),
                    example_rows=item.example_rows,
                    confidence_bp=item.manufacturer_likelihood_bp,
                )
            )
    for value, row_id in official_manufacturers:
        if normalize_identity(value) not in {
            normalize_identity(item.canonical_observed_value) for item in observed_manufacturers
        }:
            observed_manufacturers.append(
                ObservedIdentityVocabularyEntry(
                    canonical_observed_value=value,
                    normalized_variants=(normalize_identity(value),),
                    support_count=1,
                    source_fields=(IdentityEvidenceSource.OBSERVED_LABELLED_MAPPING,),
                    example_rows=(row_id,),
                    confidence_bp=9_500,
                )
            )

    leading_groups: dict[str, list[UnilogChallengeInputRow]] = defaultdict(list)
    prefix_groups: dict[str, list[UnilogChallengeInputRow]] = defaultdict(list)
    for row in rows:
        leading = leading_phrase(row.part_desc)
        if leading:
            leading_groups[normalize_identity(leading[0])].append(row)
        prefix = mpn_prefix(row.mfg_part_num)
        if prefix:
            prefix_groups[prefix].append(row)

    leading_entries = []
    for key in sorted(leading_groups):
        grouped = leading_groups[key]
        candidates = (brand_by_key[key].canonical_observed_value,) if key in brand_by_key else ()
        leading_entries.append(
            LeadingDescriptionPhraseEvidence(
                normalized_leading_phrase=key,
                canonical_phrase=leading_phrase(grouped[0].part_desc)[0],  # type: ignore[index]
                occurrence_count=len(grouped),
                distinct_product_types=len(
                    {
                        match[0].canonical
                        for row in grouped
                        if (match := matched_rule(row.part_desc)) is not None
                    }
                ),
                distinct_part_manuf_values=len(
                    {normalize_identity(row.part_manuf_raw) for row in grouped}
                ),
                distinct_mpns=len({row.mfg_part_num for row in grouped}),
                associated_brand_candidates=candidates,
                confidence_bp=8_500 if candidates and len(grouped) >= 3 else 4_000,
            )
        )

    prefix_entries = []
    for prefix in sorted(prefix_groups):
        grouped = prefix_groups[prefix]
        associated_brands = sorted(
            {value for row in grouped for value, _ in _brand_values(row)}, key=str.casefold
        )
        associated_manufacturers = sorted(
            {row.parsed_manufacturer for row in grouped if row.parsed_manufacturer},
            key=str.casefold,
        )
        if len(grouped) >= 2:
            prefix_entries.append(
                ObservedMpnPrefixEvidence(
                    prefix=prefix,
                    support_count=len(grouped),
                    associated_brand_candidates=tuple(associated_brands),
                    associated_manufacturer_candidates=tuple(associated_manufacturers),
                    confidence_bp=(
                        8_000 if len(grouped) >= 3 and len(associated_brands) == 1 else 4_000
                    ),
                )
            )

    relation_counts: Counter[tuple[str, str]] = Counter()
    org_by_key = {normalize_identity(item.parsed_name): item for item in organizations}
    for row in rows:
        if not row.parsed_manufacturer or not row.parsed_manufacturer.strip(" -"):
            continue
        for brand, _ in _brand_values(row):
            relation_counts[(normalize_identity(row.parsed_manufacturer), brand)] += 1
    manufacturer_relations: list[IdentityRelationEvidence] = []
    supplier_relations: list[IdentityRelationEvidence] = []
    for (org_key, brand), count in sorted(relation_counts.items()):
        relation = IdentityRelationEvidence(
            left_value=org_by_key[org_key].parsed_name, right_value=brand, support_count=count
        )
        target = (
            supplier_relations
            if org_by_key[org_key].supplier_likelihood_bp >= 7_500
            else manufacturer_relations
        )
        target.append(relation)

    statistics = UnilogIdentityVocabularyStatistics(
        input_rows=len(rows),
        unique_organizations=len(organizations),
        supplier_like_organizations=sum(
            item.supplier_likelihood_bp >= 7_500 for item in organizations
        ),
        non_placeholder_brand_rows=sum(bool(_brand_values(row)) for row in rows),
        description_brand_candidates=sum(
            bool(item.associated_brand_candidates) and item.occurrence_count >= 3
            for item in leading_entries
        ),
        repeated_mpn_prefixes=sum(item.support_count >= 3 for item in prefix_entries),
    )
    values: dict[str, object] = {
        "policy_version": UNILOG_IDENTITY_POLICY_VERSION,
        "input_sha256": input_sha256,
        "ground_truth_sha256": ground_truth_sha256,
        "organizations": organizations,
        "observed_manufacturers": sorted(
            observed_manufacturers, key=lambda item: item.canonical_observed_value.casefold()
        ),
        "observed_brands": observed_brands,
        "leading_description_tokens": leading_entries,
        "mpn_prefix_evidence": prefix_entries,
        "manufacturer_brand_relations": manufacturer_relations,
        "supplier_brand_relations": supplier_relations,
        "statistics": statistics,
    }
    digest = hashlib.sha256(
        json.dumps(_jsonable(values), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return UnilogManufacturerBrandEvidenceArtifact(
        artifact_hash=digest,
        **values,  # type: ignore[arg-type]
    )


def _vocabulary_entries(
    grouped: dict[str, list[tuple[str, IdentityEvidenceSource, str]]],
    official: list[tuple[str, str]],
) -> list[ObservedIdentityVocabularyEntry]:
    result = []
    for key in sorted(grouped):
        values = grouped[key]
        result.append(
            ObservedIdentityVocabularyEntry(
                canonical_observed_value=values[0][0],
                normalized_variants=(key,),
                support_count=len(values),
                source_fields=tuple(sorted({item[1] for item in values}, key=str)),
                example_rows=tuple(dict.fromkeys(item[2] for item in values))[:5],
                confidence_bp=9_000 if len(values) > 1 else 8_500,
            )
        )
    known = {normalize_identity(item.canonical_observed_value) for item in result}
    for value, row_id in official:
        if normalize_identity(value) not in known:
            result.append(
                ObservedIdentityVocabularyEntry(
                    canonical_observed_value=value,
                    normalized_variants=(normalize_identity(value),),
                    support_count=1,
                    source_fields=(IdentityEvidenceSource.OBSERVED_LABELLED_MAPPING,),
                    example_rows=(row_id,),
                    confidence_bp=9_500,
                )
            )
    return sorted(result, key=lambda item: item.canonical_observed_value.casefold())


def _jsonable(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return _jsonable(asdict(value))  # type: ignore[call-overload]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value
