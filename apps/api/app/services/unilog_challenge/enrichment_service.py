"""Evidence-grounded single-row Unilog enrichment orchestration."""

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime

from app.domain.unilog_challenge import (
    UNILOG_ENRICHMENT_POLICY_VERSION,
    EvidenceSourceType,
    EvidenceStrength,
    FieldPopulationStrategy,
    FieldProvenance,
    FieldValidationStatus,
    ObservedVocabulary,
    ResolutionStatus,
    UnilogChallengeInputRow,
    UnilogDescriptionResult,
    UnilogEnrichmentResult,
    UnilogFieldResolution,
    UnilogItemFeature,
    UnilogSemanticAttributeCandidate,
)
from app.services.unilog_attributes.attribute_delivery_mapper import UnilogAttributeDeliveryMapper
from app.services.unilog_challenge.attribute_extractor import UnilogAttributeExtractor
from app.services.unilog_challenge.classifier import UnilogChallengeClassifier
from app.services.unilog_challenge.delivery_assembler import UnilogDeliveryRecordAssembler
from app.services.unilog_challenge.description_builder import UnilogDescriptionBuilder
from app.services.unilog_challenge.description_signal_extractor import (
    UnilogDescriptionSignalExtractor,
)
from app.services.unilog_challenge.direct_field_mapper import UnilogDirectFieldMapper
from app.services.unilog_classification.rule_registry import UnilogProductTypeRuleRegistry
from app.services.unilog_identity.resolver import UnilogIdentityResolver

_ATTRIBUTE_PRIORITY = (
    "Series",
    "Model",
    "Number of Wash Cycles",
    "Voltage Rating",
    "Amperage Rating",
    "Mounting Type",
    "Plug Type",
    "Size",
    "Depth With Door Open",
    "Minimum Height",
    "Maximum Height",
    "Sound Level",
    "Material",
    "Color",
    "Additional Information",
)


class UnilogEnrichmentService:
    def __init__(
        self,
        *,
        now: Callable[[], datetime] | None = None,
        direct_mapper: UnilogDirectFieldMapper | None = None,
        signal_extractor: UnilogDescriptionSignalExtractor | None = None,
        identity_resolver: UnilogIdentityResolver | None = None,
        classifier: UnilogChallengeClassifier | None = None,
        attribute_extractor: UnilogAttributeExtractor | None = None,
        description_builder: UnilogDescriptionBuilder | None = None,
        assembler: UnilogDeliveryRecordAssembler | None = None,
    ) -> None:
        self._now = now or (lambda: datetime.now(UTC))
        self._direct = direct_mapper or UnilogDirectFieldMapper()
        self._signals = signal_extractor or UnilogDescriptionSignalExtractor()
        self._identity = identity_resolver or UnilogIdentityResolver()
        self._classifier = classifier or UnilogChallengeClassifier()
        self._attributes = attribute_extractor or UnilogAttributeExtractor()
        self._attribute_delivery = UnilogAttributeDeliveryMapper()
        self._descriptions = description_builder or UnilogDescriptionBuilder()
        self._assembler = assembler or UnilogDeliveryRecordAssembler()

    def enrich_row(
        self,
        input_row: UnilogChallengeInputRow,
        vocabulary: ObservedVocabulary | None = None,
    ) -> UnilogEnrichmentResult:
        signals = self._signals.extract(input_row)
        identity = self._identity.resolve(input_row, product_type=signals.product_type)
        classification = self._classifier.classify(signals, vocabulary)
        attributes = self._attributes.extract(signals, vocabulary)
        resolutions = list(self._direct.map(input_row))
        if identity.brand is not None and identity.brand_status is ResolutionStatus.RESOLVED:
            resolutions.append(
                self._derived_resolution(
                    "BRAND_NAME",
                    identity.brand,
                    ";".join(identity.brand_evidence),
                    identity.brand_confidence_bp,
                    strategy=FieldPopulationStrategy.DETERMINISTIC_PARSE,
                )
            )
        if (
            identity.manufacturer is not None
            and identity.manufacturer_status is ResolutionStatus.RESOLVED
        ):
            resolutions.append(
                self._derived_resolution(
                    "MANUFACTURER_NAME",
                    identity.manufacturer,
                    ";".join(identity.manufacturer_evidence),
                    identity.manufacturer_confidence_bp,
                    strategy=FieldPopulationStrategy.DETERMINISTIC_PARSE,
                )
            )
        if classification.classpath is not None:
            taxonomy_values = (
                ("Dept", classification.department),
                ("Class", classification.class_name),
                ("Fine", classification.fine),
                ("Classpath", classification.classpath),
            )
            resolutions.extend(
                self._derived_resolution(
                    field,
                    value,
                    "verified-product-type-classpath-mapping",
                    classification.classpath_confidence_bp,
                    strategy=FieldPopulationStrategy.OBSERVED_MAPPING,
                )
                for field, value in taxonomy_values
                if value is not None
            )
        resolutions.extend(self._attribute_resolutions(attributes))
        resolutions.extend(self._dimension_resolutions(signals.product_type, attributes))
        facts = self._description_facts(
            input_row,
            identity.brand if identity.brand_status is ResolutionStatus.RESOLVED else None,
            identity.manufacturer
            if identity.manufacturer_status is ResolutionStatus.RESOLVED
            else None,
            signals.product_type,
            attributes,
        )
        descriptions = self._descriptions.build_all(
            facts, raw_evidence=f"{input_row.mfg_part_num} {input_row.part_desc}"
        )
        resolutions.extend(self._description_resolutions(descriptions))
        features = self._features(attributes)
        resolutions.extend(self._feature_resolutions(features))
        record = self._assembler.assemble(resolutions)
        populated = sum(value not in (None, "") for value in record.as_dict().values())
        confidences = [item.confidence_bp for item in resolutions if item.value is not None]
        confidences.extend((identity.manufacturer_confidence_bp, identity.brand_confidence_bp))
        warnings = list(
            dict.fromkeys(
                issue for description in descriptions for issue in description.validation_issues
            )
        )
        manufacturer_reasons = {
            reason.value
            for reason in identity.review_reasons
            if reason.value.startswith("MANUFACTURER")
            or reason.value in {"SUPPLIER_ONLY_EVIDENCE", "ORGANIZATION_ROLE_AMBIGUOUS"}
        }
        brand_reasons = {
            reason.value
            for reason in identity.review_reasons
            if reason.value.startswith("BRAND")
            or reason.value in {"DESCRIPTION_BRAND_WEAK", "MPN_PREFIX_WEAK"}
        }
        if manufacturer_reasons:
            warnings.append("MANUFACTURER_REVIEW_REQUIRED")
        if brand_reasons:
            warnings.append("BRAND_REVIEW_REQUIRED")
        warnings.extend(f"IDENTITY:{reason.value}" for reason in identity.review_reasons)
        if classification.review_required:
            warnings.append("CLASSIFICATION_REVIEW_REQUIRED")
            warnings.extend(reason.value for reason in classification.review_reasons)
        if any(item.review_required for item in attributes):
            warnings.append("ATTRIBUTE_CONFLICT_REVIEW_REQUIRED")
        review_required = bool(warnings)
        enrichment_id = hashlib.sha256(
            f"{input_row.row_id}:{UNILOG_ENRICHMENT_POLICY_VERSION}:deterministic:none:none".encode()
        ).hexdigest()
        return UnilogEnrichmentResult(
            enrichment_id=enrichment_id,
            input_row_id=input_row.row_id,
            delivery_record=record,
            field_resolutions=tuple(resolutions),
            attributes=attributes,
            features=features,
            descriptions=descriptions,
            classification=classification,
            review_required=review_required,
            overall_confidence_bp=sum(confidences) // len(confidences) if confidences else 0,
            populated_field_count=populated,
            supported_field_count=populated,
            total_field_count=252,
            warnings=tuple(dict.fromkeys(warnings)),
            created_at=self._now(),
            policy_version=UNILOG_ENRICHMENT_POLICY_VERSION,
        )

    @staticmethod
    def _derived_resolution(
        field: str,
        value: str,
        source: str,
        confidence_bp: int,
        *,
        strategy: FieldPopulationStrategy,
        review_required: bool = False,
    ) -> UnilogFieldResolution:
        provenance = FieldProvenance(
            field_name=field,
            value=value,
            source_type=(
                EvidenceSourceType.OFFICIAL_LABELLED_OUTPUT_MAPPING
                if strategy is FieldPopulationStrategy.OBSERVED_MAPPING
                else EvidenceSourceType.DETERMINISTIC_PARSE
            ),
            source_reference=source,
            method="unilog-enrichment-policy-v1",
            evidence_strength=EvidenceStrength.DERIVED,
            confidence_bp=confidence_bp,
            review_required=review_required,
        )
        return UnilogFieldResolution(
            field_name=field,
            value=value,
            strategy=strategy,
            validation_status=(
                FieldValidationStatus.VALID_WITH_WARNING
                if review_required
                else FieldValidationStatus.VALID
            ),
            provenance=provenance,
            confidence_bp=confidence_bp,
            review_required=review_required,
        )

    def _attribute_resolutions(
        self, attributes: tuple[UnilogSemanticAttributeCandidate, ...]
    ) -> tuple[UnilogFieldResolution, ...]:
        ordered = sorted(
            self._attribute_delivery.assign_slots(attributes),
            key=lambda item: (
                item[0],
                _ATTRIBUTE_PRIORITY.index(item[1].official_label)
                if item[1].official_label in _ATTRIBUTE_PRIORITY
                else len(_ATTRIBUTE_PRIORITY),
                item[1].evidence_span,
            ),
        )
        resolutions: list[UnilogFieldResolution] = []
        for index, item in ordered:
            resolutions.append(
                self._derived_resolution(
                    f"ATTRIBUTE_LABEL {index}",
                    item.official_label or item.semantic_name,
                    item.fact_id,
                    item.confidence_bp,
                    strategy=FieldPopulationStrategy.ATTRIBUTE_DERIVED,
                )
            )
            resolutions.append(
                self._derived_resolution(
                    f"ATTRIBUTE_VALUE {index}",
                    item.normalized_value,
                    item.fact_id,
                    item.confidence_bp,
                    strategy=FieldPopulationStrategy.ATTRIBUTE_DERIVED,
                )
            )
            if item.uom:
                resolutions.append(
                    self._derived_resolution(
                        f"ATTRIBUTE_UOM {index}",
                        item.uom,
                        item.fact_id,
                        item.confidence_bp,
                        strategy=FieldPopulationStrategy.ATTRIBUTE_DERIVED,
                    )
                )
        return tuple(resolutions)

    def _dimension_resolutions(
        self, product_type: str | None, attributes: tuple[UnilogSemanticAttributeCandidate, ...]
    ) -> tuple[UnilogFieldResolution, ...]:
        expected_dimensions = UnilogProductTypeRuleRegistry.dimension_interpretation(product_type)
        if expected_dimensions is None:
            return ()
        dimensions = [item for item in attributes if item.semantic_name in expected_dimensions]
        if len(dimensions) != 2 or any(item.review_required for item in dimensions):
            return ()
        resolutions: list[UnilogFieldResolution] = []
        for item in dimensions:
            field = item.semantic_name.upper()
            resolutions.append(
                self._derived_resolution(
                    field,
                    item.normalized_value,
                    item.fact_id,
                    item.confidence_bp,
                    strategy=FieldPopulationStrategy.ATTRIBUTE_DERIVED,
                )
            )
            if item.uom:
                resolutions.append(
                    self._derived_resolution(
                        f"{field}_UOM",
                        item.uom,
                        item.fact_id,
                        item.confidence_bp,
                        strategy=FieldPopulationStrategy.ATTRIBUTE_DERIVED,
                    )
                )
        return tuple(resolutions)

    @staticmethod
    def _description_facts(
        row: UnilogChallengeInputRow,
        brand: str | None,
        manufacturer: str | None,
        product_type: str | None,
        attributes: tuple[UnilogSemanticAttributeCandidate, ...],
    ) -> dict[str, str]:
        facts = {"mpn": row.mfg_part_num}
        for key, value in (
            ("brand", brand),
            ("manufacturer", manufacturer),
            ("product_type", product_type),
        ):
            if value:
                facts[key] = value
        by_name = {item.semantic_name: item for item in attributes if not item.review_required}
        if "Series" in by_name:
            facts["series"] = by_name["Series"].normalized_value
        if "Material" in by_name:
            facts["material"] = by_name["Material"].normalized_value
        if "Grit" in by_name:
            facts["grit"] = by_name["Grit"].normalized_value
        if "Package Quantity" in by_name:
            facts["quantity"] = f"{by_name['Package Quantity'].normalized_value} pc"
        if "Width" in by_name and "Length" in by_name:
            width, length = by_name["Width"], by_name["Length"]
            facts["dimensions"] = (
                f"{width.normalized_value} x {length.normalized_value} {length.uom or ''}".strip()
            )
        return facts

    def _description_resolutions(
        self, descriptions: tuple[UnilogDescriptionResult, ...]
    ) -> tuple[UnilogFieldResolution, ...]:
        return tuple(
            UnilogFieldResolution(
                field_name=item.field_name,
                value=item.value,
                strategy=FieldPopulationStrategy.DESCRIPTION_CONSTRUCTED,
                validation_status=(
                    FieldValidationStatus.MISSING
                    if item.value is None
                    else FieldValidationStatus.VALID_WITH_WARNING
                    if item.validation_issues
                    else FieldValidationStatus.VALID
                ),
                provenance=item.field_provenance[0] if item.field_provenance else None,
                confidence_bp=item.confidence_bp,
                review_required=bool(item.validation_issues),
                issues=item.validation_issues,
            )
            for item in descriptions
        )

    @staticmethod
    def _features(
        attributes: tuple[UnilogSemanticAttributeCandidate, ...],
    ) -> tuple[UnilogItemFeature, ...]:
        features: list[UnilogItemFeature] = []
        for item in attributes:
            if item.review_required or item.semantic_name in ("Width", "Length", "Series"):
                continue
            text = (
                f"{item.normalized_value} grit"
                if item.semantic_name == "Grit"
                else f"{item.normalized_value} pc"
                if item.semantic_name == "Package Quantity"
                else item.normalized_value
            )
            features.append(
                UnilogItemFeature(
                    value=text, fact_ids=(item.fact_id,), confidence_bp=item.confidence_bp
                )
            )
        return tuple(features[:20])

    def _feature_resolutions(
        self, features: tuple[UnilogItemFeature, ...]
    ) -> tuple[UnilogFieldResolution, ...]:
        return tuple(
            self._derived_resolution(
                f"ITEM_FEATURES_{index}",
                item.value,
                item.fact_ids[0],
                item.confidence_bp,
                strategy=FieldPopulationStrategy.ATTRIBUTE_DERIVED,
            )
            for index, item in enumerate(features, start=1)
        )


def enrich_row(
    input_row: UnilogChallengeInputRow,
    vocabulary: ObservedVocabulary | None = None,
) -> UnilogEnrichmentResult:
    return UnilogEnrichmentService().enrich_row(input_row, vocabulary)
