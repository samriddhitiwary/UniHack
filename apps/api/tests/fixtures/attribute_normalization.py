from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.attribute_extraction import (
    AttributeCandidate,
    AttributeExtractionEvidenceType,
    AttributeMatchType,
    AttributeValueParseStatus,
    StructuredAttributeExtractionResult,
)
from app.domain.category_schemas import CategoryAttributeSchema

NOW = datetime(2026, 8, 13, tzinfo=UTC)
PRODUCT_ID = UUID("22222222-2222-4222-8222-222222222222")
CLASSIFICATION_ID = UUID("33333333-3333-4333-8333-333333333333")


def candidate(
    schema: CategoryAttributeSchema,
    attribute_name: str,
    raw_value: str | None,
    raw_unit: str | None,
    *,
    index: int = 1,
) -> AttributeCandidate:
    attribute = next(item for item in schema.attributes if item.canonical_name == attribute_name)
    return AttributeCandidate(
        candidate_id=f"candidate-{index:06d}",
        attribute_name=attribute_name,
        attribute_display_name=attribute.display_name,
        attribute_data_type=attribute.data_type,
        raw_value=raw_value,
        raw_unit=raw_unit,
        source_id=uuid4(),
        evidence_id=f"evidence-{index:06d}",
        evidence_type=AttributeExtractionEvidenceType.DIRECT_TEXT,
        location=f"line={index}",
        excerpt=f"{attribute.display_name}: {raw_value}",
        matched_label=attribute.display_name,
        match_type=AttributeMatchType.EXACT,
        confidence_bp=9_000,
        source_quality_bp=9_000,
        parse_status=(
            AttributeValueParseStatus.MISSING_VALUE
            if raw_value is None
            else AttributeValueParseStatus.PARSED
        ),
        created_at=NOW,
    )


def extraction(schema: CategoryAttributeSchema, candidates: tuple[AttributeCandidate, ...]):
    return StructuredAttributeExtractionResult.create(
        job_id=uuid4(),
        product_id=PRODUCT_ID,
        classification_id=CLASSIFICATION_ID,
        category=schema.category,
        schema_version=schema.version,
        schema_fingerprint=schema.schema_fingerprint,
        evidence_item_count=len(candidates),
        candidates=candidates,
        duplicate_count=0,
        warning_codes=(),
        now=NOW,
    )
