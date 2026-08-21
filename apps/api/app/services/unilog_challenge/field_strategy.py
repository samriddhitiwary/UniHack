"""Single authoritative population strategy registry for all 252 delivery fields."""

from dataclasses import dataclass

from app.domain.unilog_challenge import FieldPopulationStrategy
from app.domain.unilog_challenge.delivery_schema import UNILOG_DELIVERY_HEADERS

_DIRECT = frozenset(
    {
        "Mfg_Part_Num",
        "Part_Desc",
        "E1_Brand",
        "Unilog_Brand",
        "DIB_Brand",
        "Part_Manuf",
        "MANUFACTURER_PART_NUMBER",
    }
)
_RESOLVED = frozenset({"MANUFACTURER_NAME", "BRAND_NAME"})
_OBSERVED = frozenset({"Dept", "Class", "Fine", "Classpath"})
_DESCRIPTIONS = frozenset(
    {
        "Product Name",
        "MOBILE_DESC",
        "INVOICE_DESC",
        "SHORT_DESC",
        "LONG_DESC1",
        "RETAIL_DESC",
        "MARKETING_DESCRIPTION",
    }
)
_ATTRIBUTE_DERIVED = frozenset(
    {
        "With",
        "Standard/Approvals",
        "Prop 65",
        "Application",
        "Includes",
        "Standard Packaging Information",
        "LENGTH",
        "LENGTH_UOM",
        "HEIGHT",
        "HEIGHT_UOM",
        "WIDTH",
        "WIDTH_UOM",
        "WEIGHT",
        "WEIGHT_UOM",
        "VOLUME",
        "VOLUME_UOM",
    }
)
_EXTERNAL = frozenset(
    {
        "MFR URL",
        *(f"Ref URL {index}" for index in range(1, 6)),
        "PART_NUMBER",
        "SKU - MY_PART_NUMBER",
        "UPC",
        "EAN",
        "GTIN",
        "UNSPSC",
        "Warranty",
        "List Price",
        "Selling Qty",
        "Selling UOM",
        "Product Image",
        *(f"Alternate Image {index}" for index in range(1, 5)),
        "SDS",
        "SDS_1",
        "Warranty Information",
        "Catalog",
        "Specification Sheet",
        "Instruction/Installation Manual",
        "Service Manual",
        "Owners/User Manual",
        "Line Drawing",
        "MTR",
        "RoHS",
        "Full Engineering Drawing",
        "Energy Star Guide",
        "Technical Bulletin",
        "Submittal",
        "Compatibility Chart",
        "Size Chart",
        "Product Label/Insert",
        "Video Link",
        "Video Link 1",
        "Country Of Origin",
        "Discontinued",
        "Actual Image (Yes/No)",
    }
)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogFieldStrategyEntry:
    field: str
    strategy: FieldPopulationStrategy
    possible_source: str
    validation: str
    confidence_behavior: str
    blank_behavior: str = "Empty CSV cell when evidence is unavailable or invalid."


class UnilogFieldPopulationStrategy:
    """Classify every canonical field without scattering population policy."""

    def entries(self) -> tuple[UnilogFieldStrategyEntry, ...]:
        return tuple(self.for_field(field) for field in UNILOG_DELIVERY_HEADERS)

    def for_field(self, field: str) -> UnilogFieldStrategyEntry:
        if field not in UNILOG_DELIVERY_HEADERS:
            raise KeyError(field)
        strategy = self._strategy(field)
        source, validation, confidence = _PROFILE[strategy]
        return UnilogFieldStrategyEntry(
            field=field,
            strategy=strategy,
            possible_source=source,
            validation=validation,
            confidence_behavior=confidence,
        )

    @staticmethod
    def _strategy(field: str) -> FieldPopulationStrategy:
        if field in _DIRECT:
            return FieldPopulationStrategy.DIRECT_COPY
        if field in _RESOLVED:
            return FieldPopulationStrategy.DETERMINISTIC_PARSE
        if field in _OBSERVED:
            return FieldPopulationStrategy.OBSERVED_MAPPING
        if field in _DESCRIPTIONS:
            return FieldPopulationStrategy.DESCRIPTION_CONSTRUCTED
        if field.startswith("ATTRIBUTE_") or field.startswith("ITEM_FEATURES_"):
            return FieldPopulationStrategy.ATTRIBUTE_DERIVED
        if field in _ATTRIBUTE_DERIVED:
            return FieldPopulationStrategy.ATTRIBUTE_DERIVED
        if field in _EXTERNAL:
            return FieldPopulationStrategy.EXTERNAL_ONLY
        return FieldPopulationStrategy.UNSUPPORTED


_PROFILE = {
    FieldPopulationStrategy.DIRECT_COPY: (
        "Exact official input cell.",
        "Exact semantic mapping and MPN formatting preservation.",
        "10000 bp; no review after schema validation.",
    ),
    FieldPopulationStrategy.DETERMINISTIC_PARSE: (
        "Cleansed organizer evidence and corroborated description evidence.",
        "Placeholder exclusion, supplier distinction, normalized agreement.",
        "8500-9500 bp when resolved; ambiguous candidates remain blank/reviewable.",
    ),
    FieldPopulationStrategy.OBSERVED_MAPPING: (
        "General pattern or vocabulary from official labelled rows.",
        "Must match observed vocabulary; never retrieve the evaluated row answer.",
        "At least 9000 bp for an exact supported rule; otherwise blank/reviewable.",
    ),
    FieldPopulationStrategy.ATTRIBUTE_DERIVED: (
        "Deterministically parsed description signal or validated attribute.",
        "Evidence span, supported label, triple integrity, unit and conflict checks.",
        "At least 8500 bp; conflicts and unknown official labels do not populate.",
    ),
    FieldPopulationStrategy.DESCRIPTION_CONSTRUCTED: (
        "Trusted resolved facts only.",
        "Grounding, numeric traceability, case, length, and duplicate checks.",
        "Minimum source confidence; warnings require review, invalid content is blank.",
    ),
    FieldPopulationStrategy.MODEL_ASSISTED: (
        "Validated structured model proposal using trusted facts only.",
        "Exact source-span grounding, bounded schema, at most two attempts.",
        "At least 8500 bp and reviewable; deterministic fallback on failure.",
    ),
    FieldPopulationStrategy.EXTERNAL_ONLY: (
        "Official manufacturer/organizer source or human review.",
        "Source existence, semantic validation, and provenance required.",
        "Populated only from direct trusted evidence; otherwise unsupported blank.",
    ),
    FieldPopulationStrategy.UNSUPPORTED: (
        "No safe source in SPEC-042.",
        "Population is prohibited by policy.",
        "No confidence is assigned because the field remains blank.",
    ),
}

if len(UnilogFieldPopulationStrategy().entries()) != 252:
    raise RuntimeError("every Unilog delivery field must have one strategy entry")
