"""Independent manufacturer, brand, and supplier resolution from indexed evidence."""

from collections import defaultdict

from app.domain.unilog_challenge import ResolutionStatus, UnilogChallengeInputRow
from app.domain.unilog_identity import (
    IdentityReviewReason,
    ManufacturerResolutionResult,
    UnilogManufacturerBrandEvidenceArtifact,
)
from app.services.unilog_identity.normalization import (
    compact_identity,
    leading_phrase,
    mpn_prefix,
    normalize_identity,
)
from app.services.unilog_identity.supplier_classifier import SupplierEvidenceClassifier
from app.services.unilog_identity.vocabulary_store import load_default_identity_artifact


class UnilogIdentityEvidenceIndex:
    def __init__(self, artifact: UnilogManufacturerBrandEvidenceArtifact) -> None:
        self.organizations = {
            normalize_identity(item.parsed_name): item for item in artifact.organizations
        }
        self.brands = {
            variant: item
            for item in artifact.observed_brands
            for variant in item.normalized_variants
        }
        self.manufacturers = {
            variant: item
            for item in artifact.observed_manufacturers
            for variant in item.normalized_variants
        }
        self.leading = {
            item.normalized_leading_phrase: item for item in artifact.leading_description_tokens
        }
        self.prefixes = {item.prefix: item for item in artifact.mpn_prefix_evidence}
        relations: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for item in artifact.manufacturer_brand_relations:
            relations[normalize_identity(item.left_value)].append(
                (item.right_value, item.support_count)
            )
        self.manufacturer_brands = dict(relations)
        inverse: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for organization, values in self.manufacturer_brands.items():
            for brand, count in values:
                inverse[normalize_identity(brand)].append((organization, count))
        self.brand_manufacturers = dict(inverse)


class UnilogIdentityResolver:
    def __init__(self, artifact: UnilogManufacturerBrandEvidenceArtifact | None = None) -> None:
        self.artifact = artifact or load_default_identity_artifact()
        self.index = UnilogIdentityEvidenceIndex(self.artifact)

    def resolve(
        self, row: UnilogChallengeInputRow, *, product_type: str | None = None
    ) -> ManufacturerResolutionResult:
        brand, brand_status, brand_confidence, brand_evidence, brand_reasons = self._brand(
            row, product_type=product_type
        )
        (
            manufacturer,
            supplier,
            manufacturer_status,
            manufacturer_confidence,
            manufacturer_evidence,
            manufacturer_reasons,
        ) = self._manufacturer(row, brand)
        reasons = tuple(dict.fromkeys((*manufacturer_reasons, *brand_reasons)))
        return ManufacturerResolutionResult(
            manufacturer=manufacturer,
            brand=brand,
            supplier_organization=supplier,
            manufacturer_status=manufacturer_status,
            brand_status=brand_status,
            manufacturer_confidence_bp=manufacturer_confidence,
            brand_confidence_bp=brand_confidence,
            manufacturer_evidence=manufacturer_evidence,
            brand_evidence=brand_evidence,
            review_required=bool(reasons),
            review_reasons=reasons,
        )

    def _brand(
        self, row: UnilogChallengeInputRow, *, product_type: str | None
    ) -> tuple[
        str | None, ResolutionStatus, int, tuple[str, ...], tuple[IdentityReviewReason, ...]
    ]:
        supplied = tuple(
            (source, value)
            for source, value in (
                ("E1_BRAND", row.e1_brand_clean),
                ("UNILOG_BRAND", row.unilog_brand_clean),
                ("DIB_BRAND", row.dib_brand_clean),
            )
            if value is not None
        )
        grouped: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for source, value in supplied:
            grouped[normalize_identity(value)].append((source, value))
        if len(grouped) > 1:
            return (
                None,
                ResolutionStatus.AMBIGUOUS,
                2_500,
                tuple(
                    f"{source}:{value}" for values in grouped.values() for source, value in values
                ),
                (IdentityReviewReason.BRAND_FIELD_CONFLICT, IdentityReviewReason.BRAND_AMBIGUOUS),
            )
        if grouped:
            values = next(iter(grouped.values()))
            canonical = self.index.brands[normalize_identity(values[0][1])].canonical_observed_value
            confidence = 9_700 if len(values) > 1 else 9_200
            return (
                canonical,
                ResolutionStatus.RESOLVED,
                confidence,
                tuple(f"{source}:{value}" for source, value in values),
                (),
            )

        candidates: dict[str, list[str]] = defaultdict(list)
        leading = leading_phrase(row.part_desc)
        if leading:
            item = self.index.leading.get(normalize_identity(leading[0]))
            repeats_product_type = bool(
                product_type and normalize_identity(leading[0]) == normalize_identity(product_type)
            )
            if (
                item
                and not repeats_product_type
                and item.occurrence_count >= 3
                and len(item.associated_brand_candidates) == 1
            ):
                candidates[normalize_identity(item.associated_brand_candidates[0])].append(
                    f"PART_DESC:{leading[0]}"
                )
        prefix = mpn_prefix(row.mfg_part_num)
        prefix_item = self.index.prefixes.get(prefix or "")
        if (
            prefix_item
            and prefix_item.support_count >= 3
            and len(prefix_item.associated_brand_candidates) == 1
        ):
            candidates[normalize_identity(prefix_item.associated_brand_candidates[0])].append(
                f"MPN_PREFIX:{prefix_item.prefix}"
            )
        org_key = normalize_identity(row.parsed_manufacturer or "")
        relations = self.index.manufacturer_brands.get(org_key, [])
        strong_relations = [(value, count) for value, count in relations if count >= 3]
        if len(strong_relations) == 1:
            value, count = strong_relations[0]
            org_compact = compact_identity(row.parsed_manufacturer or "")
            brand_compact = compact_identity(value)
            organization = self.index.organizations.get(org_key)
            if organization and (
                brand_compact in org_compact
                or org_compact in brand_compact
                or organization.manufacturer_likelihood_bp >= 8_000
            ):
                candidates[normalize_identity(value)].append(f"DATASET_RELATION:{count}")
        if len(candidates) == 1:
            key, evidence = next(iter(candidates.items()))
            canonical = self.index.brands[key].canonical_observed_value
            confidence = min(9_000, 7_800 + 400 * len(evidence))
            return canonical, ResolutionStatus.RESOLVED, confidence, tuple(evidence), ()
        if len(candidates) > 1:
            return (
                None,
                ResolutionStatus.AMBIGUOUS,
                3_500,
                tuple(evidence for values in candidates.values() for evidence in values),
                (IdentityReviewReason.BRAND_AMBIGUOUS,),
            )
        weak: tuple[IdentityReviewReason, ...] = ()
        if prefix_item and prefix_item.support_count < 3:
            weak = (IdentityReviewReason.MPN_PREFIX_WEAK,)
        return (
            None,
            ResolutionStatus.NOT_FOUND,
            0,
            (),
            (*weak, IdentityReviewReason.BRAND_UNRESOLVED),
        )

    def _manufacturer(
        self, row: UnilogChallengeInputRow, brand: str | None
    ) -> tuple[
        str | None,
        str | None,
        ResolutionStatus,
        int,
        tuple[str, ...],
        tuple[IdentityReviewReason, ...],
    ]:
        if not row.parsed_manufacturer or not row.parsed_manufacturer.strip(" -"):
            return (
                None,
                None,
                ResolutionStatus.MISSING,
                0,
                (),
                (IdentityReviewReason.MANUFACTURER_UNRESOLVED,),
            )
        key = normalize_identity(row.parsed_manufacturer)
        organization = self.index.organizations.get(key)
        if organization is None:
            current = SupplierEvidenceClassifier().classify(row.part_manuf_raw)
            brand_agrees = bool(
                current
                and brand
                and compact_identity(brand) in compact_identity(current.parsed_name)
            )
            if current and brand_agrees and current.supplier_likelihood_bp < 7_500:
                return (
                    current.parsed_name,
                    None,
                    ResolutionStatus.RESOLVED,
                    8_000,
                    (f"PART_MANUF:{current.parsed_name}", f"BRAND_AGREEMENT:{brand}"),
                    (),
                )
            return (
                None,
                None,
                ResolutionStatus.NOT_FOUND,
                0,
                (),
                (IdentityReviewReason.MANUFACTURER_UNRESOLVED,),
            )
        evidence = (f"PART_MANUF:{organization.parsed_name}", *organization.evidence_reasons)
        if organization.supplier_likelihood_bp >= 7_500:
            return (
                None,
                organization.parsed_name,
                ResolutionStatus.NOT_FOUND,
                1_500,
                evidence,
                (IdentityReviewReason.SUPPLIER_ONLY_EVIDENCE,),
            )
        vocabulary = self.index.manufacturers.get(key)
        relation_support = max(
            (
                count
                for value, count in self.index.manufacturer_brands.get(key, [])
                if brand and normalize_identity(value) == normalize_identity(brand)
            ),
            default=0,
        )
        brand_agrees = bool(
            brand
            and (
                compact_identity(brand) in compact_identity(organization.parsed_name)
                or compact_identity(organization.parsed_name) in compact_identity(brand)
            )
        )
        role_supported = bool(
            vocabulary
            and (
                organization.manufacturer_likelihood_bp >= 8_000
                or brand_agrees
                or (
                    relation_support >= 3
                    and organization.parsed_name.casefold().endswith((" inc", " llc"))
                )
            )
        )
        if role_supported and vocabulary:
            confidence = min(
                9_300, organization.manufacturer_likelihood_bp + min(800, relation_support * 50)
            )
            return (
                vocabulary.canonical_observed_value,
                None,
                ResolutionStatus.RESOLVED,
                confidence,
                (
                    *evidence,
                    f"RELATION_SUPPORT:{relation_support}"
                    if relation_support
                    else "ROLE_SUPPORTED",
                ),
                (),
            )
        return (
            None,
            None,
            ResolutionStatus.AMBIGUOUS,
            4_000,
            evidence,
            (
                IdentityReviewReason.ORGANIZATION_ROLE_AMBIGUOUS,
                IdentityReviewReason.MANUFACTURER_AMBIGUOUS,
            ),
        )
