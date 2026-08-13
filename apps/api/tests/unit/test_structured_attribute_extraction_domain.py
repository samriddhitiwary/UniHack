from datetime import UTC, datetime
from uuid import UUID

from app.domain.attribute_extraction import (
    StructuredAttributeExtractionResult,
    StructuredAttributeExtractionStatus,
)
from app.domain.products import ProductCategory


def test_no_candidates_is_a_successful_result() -> None:
    result = StructuredAttributeExtractionResult.create(
        job_id=UUID("11111111-1111-4111-8111-111111111111"),
        product_id=UUID("22222222-2222-4222-8222-222222222222"),
        classification_id=UUID("33333333-3333-4333-8333-333333333333"),
        category=ProductCategory.INDUCTION_MOTOR,
        schema_version=1,
        schema_fingerprint="a" * 64,
        evidence_item_count=0,
        candidates=(),
        duplicate_count=0,
        warning_codes=(),
        now=datetime(2026, 8, 13, tzinfo=UTC),
    )
    assert result.status is StructuredAttributeExtractionStatus.NO_CANDIDATES
    assert result.engine == "deterministic-schema-extractor-v1"
