"""Build bounded trusted facts from an immutable catalog projection."""

from app.core.exceptions import CatalogEnrichmentTrustedFactLimitError
from app.domain.catalog_enrichment import TrustedCatalogFact, TrustedCatalogFacts
from app.domain.catalog_projection import CommerceCatalogProjection


class CatalogEnrichmentTrustedFactBuilder:
    def __init__(self, *, max_facts: int, max_value_characters: int) -> None:
        self._max_facts = max_facts
        self._max_value_characters = max_value_characters

    def build(self, projection: CommerceCatalogProjection) -> TrustedCatalogFacts:
        facts = [
            self._fact("IDENTITY:name", "Product name", projection.product_name),
            self._fact("IDENTITY:category", "Category", projection.category.value),
        ]
        optional = (
            ("IDENTITY:manufacturer", "Manufacturer", projection.manufacturer),
            ("IDENTITY:modelNumber", "Model number", projection.model_number),
            ("IDENTITY:description", "Existing description", projection.description),
        )
        facts.extend(
            self._fact(identifier, label, value) for identifier, label, value in optional if value
        )
        facts.extend(
            TrustedCatalogFact(
                fact_id=f"ATTRIBUTE:{attribute.attribute_name}",
                display_name=attribute.attribute_display_name,
                value=self._bounded(attribute.value),
                unit=attribute.unit,
                origin=attribute.origin.value,
                validation_status=(
                    attribute.validation_status.value if attribute.validation_status else None
                ),
            )
            for attribute in projection.attributes
        )
        if len(facts) > self._max_facts:
            raise CatalogEnrichmentTrustedFactLimitError()
        return TrustedCatalogFacts(
            product_id=projection.product_id,
            projection_id=projection.projection_id,
            product_name=projection.product_name,
            manufacturer=projection.manufacturer,
            model_number=projection.model_number,
            category=projection.category,
            description=projection.description,
            facts=tuple(facts),
            warning_reason_codes=projection.warning_reason_codes,
            schema_version=projection.schema_version,
            schema_fingerprint=projection.schema_fingerprint,
        )

    def _fact(self, fact_id: str, label: str, value: str) -> TrustedCatalogFact:
        return TrustedCatalogFact(
            fact_id=fact_id,
            display_name=label,
            value=self._bounded(value),
        )

    def _bounded(self, value: str) -> str:
        if len(value) > self._max_value_characters:
            raise CatalogEnrichmentTrustedFactLimitError()
        return value
