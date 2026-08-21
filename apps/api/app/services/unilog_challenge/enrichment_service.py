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
from app.services.unilog_challenge.attribute_extractor import UnilogAttributeExtractor
from app.services.unilog_challenge.brand_resolver import UnilogChallengeBrandResolver
from app.services.unilog_challenge.classifier import UnilogChallengeClassifier
from app.services.unilog_challenge.delivery_assembler import UnilogDeliveryRecordAssembler
from app.services.unilog_challenge.description_builder import UnilogDescriptionBuilder
from app.services.unilog_challenge.description_signal_extractor import (
    UnilogDescriptionSignalExtractor,
)
from app.services.unilog_challenge.direct_field_mapper import UnilogDirectFieldMapper
from app.services.unilog_challenge.manufacturer_resolver import (
    UnilogChallengeManufacturerResolver,
)

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
        brand_resolver: UnilogChallengeBrandResolver | None = None,
        manufacturer_resolver: UnilogChallengeManufacturerResolver | None = None,
        classifier: UnilogChallengeClassifier | None = None,
        attribute_extractor: UnilogAttributeExtractor | None = None,
        description_builder: UnilogDescriptionBuilder | None = None,
        assembler: UnilogDeliveryRecordAssembler | None = None,
    ) -> None:
        self._now = now or (lambda: datetime.now(UTC))
        self._direct = direct_mapper or UnilogDirectFieldMapper()
        self._signals = signal_extractor or UnilogDescriptionSignalExtractor()
        self._brands = brand_resolver or UnilogChallengeBrandResolver()
        self._manufacturers = manufacturer_resolver or UnilogChallengeManufacturerResolver()
        self._classifier = classifier or UnilogChallengeClassifier()
        self._attributes = attribute_extractor or UnilogAttributeExtractor()
        self._descriptions = description_builder or UnilogDescriptionBuilder()
        self._assembler = assembler or UnilogDeliveryRecordAssembler()

    def enrich_row(
        self,
        input_row: UnilogChallengeInputRow,
        vocabulary: ObservedVocabulary | None = None,
    ) -> UnilogEnrichmentResult:
        signals = self._signals.extract(input_row)
        brand = self._brands.resolve(input_row, vocabulary)
        manufacturer = self._manufacturers.resolve(input_row, brand)
        classification = self._classifier.classify(signals, vocabulary)
        attributes = self._attributes.extract(signals, vocabulary)
        resolutions = list(self._direct.map(input_row))
        if brand.value is not None and brand.status is ResolutionStatus.RESOLVED:
            resolutions.append(
                self._derived_resolution(
                    "BRAND_NAME",
                    brand.value,
                    "brand-evidence",
                    brand.confidence_bp,
                    strategy=FieldPopulationStrategy.DETERMINISTIC_PARSE,
                )
            )
        if (
            manufacturer.candidate_manufacturer is not None
            and manufacturer.status is ResolutionStatus.RESOLVED
        ):
            resolutions.append(
                self._derived_resolution(
                    "MANUFACTURER_NAME",
                    manufacturer.candidate_manufacturer,
                    "manufacturer-evidence",
                    manufacturer.confidence_bp,
                    strategy=FieldPopulationStrategy.DETERMINISTIC_PARSE,
                )
            )
        if classification.classpath is not None:
            resolutions.append(
                self._derived_resolution(
                    "Classpath",
                    classification.classpath,
                    "official-labelled-classpath-pattern",
                    classification.confidence_bp,
                    strategy=FieldPopulationStrategy.OBSERVED_MAPPING,
                )
            )
        resolutions.extend(self._attribute_resolutions(attributes))
        resolutions.extend(self._dimension_resolutions(signals.product_type, attributes))
        facts = self._description_facts(
            input_row,
            brand.value if brand.status is ResolutionStatus.RESOLVED else None,
            manufacturer.candidate_manufacturer
            if manufacturer.status is ResolutionStatus.RESOLVED
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
        warnings = list(
            dict.fromkeys(
                issue for description in descriptions for issue in description.validation_issues
            )
        )
        if manufacturer.review_required:
            warnings.append("MANUFACTURER_REVIEW_REQUIRED")
        if brand.review_required:
            warnings.append("BRAND_REVIEW_REQUIRED")
        if classification.review_required:
            warnings.append("CLASSIFICATION_REVIEW_REQUIRED")
        if any(item.review_required for item in attributes):
            warnings.append("ATTRIBUTE_CONFLICT_REVIEW_REQUIRED")
        review_required = bool(warnings)
        identity = hashlib.sha256(
            f"{input_row.row_id}:{UNILOG_ENRICHMENT_POLICY_VERSION}:deterministic:none:none".encode()
        ).hexdigest()
        return UnilogEnrichmentResult(
            enrichment_id=identity,
            input_row_id=input_row.row_id,
            delivery_record=record,
            field_resolutions=tuple(resolutions),
            attributes=attributes,
            features=features,
            descriptions=descriptions,
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
            (item for item in attributes if item.official_label and not item.review_required),
            key=lambda item: (
                _ATTRIBUTE_PRIORITY.index(item.official_label)
                if item.official_label in _ATTRIBUTE_PRIORITY
                else len(_ATTRIBUTE_PRIORITY),
                item.evidence_span,
            ),
        )[:50]
        resolutions: list[UnilogFieldResolution] = []
        for index, item in enumerate(ordered, start=1):
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
        if product_type != "Sanding Belt":
            return ()
        dimensions = [item for item in attributes if item.semantic_name in ("Width", "Length")]
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
