"""Composite classification serialization tests."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.core.exceptions import ProductClassificationSerializationError
from app.domain.product_classification import (
    ClassificationEvidence,
    ClassificationEvidenceType,
    ProductClassificationResult,
)
from app.services.product_classification_engine import ProductClassificationEngine
from app.utils.dynamodb import (
    deserialize_item,
    product_classification_match_to_item,
    product_classification_metadata_to_item,
    product_classification_result_from_items,
    serialize_item,
)


def make_result() -> ProductClassificationResult:
    source_id = uuid4()
    evidence = ClassificationEvidence(
        evidence_id="evidence-000001",
        source_id=source_id,
        evidence_type=ClassificationEvidenceType.CSV_HEADER,
        text="centrifugal pump",
        location="columnIndex=0",
        weight=110,
    )
    decision = ProductClassificationEngine().classify((evidence,))
    return ProductClassificationResult.create(
        job_id=uuid4(),
        product_id=uuid4(),
        decision=decision,
        evidence_item_count=1,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_meta_is_sparse_and_round_trip_preserves_matches() -> None:
    result = make_result()
    metadata = product_classification_metadata_to_item(result)
    records = [metadata] + [
        product_classification_match_to_item(result.classification_id, index, match)
        for index, match in enumerate(result.matches, start=1)
    ]
    restored = product_classification_result_from_items(
        [deserialize_item(serialize_item(record)) for record in records]
    )
    assert metadata["recordKey"] == "META"
    assert all("jobId" not in item for item in records[1:])
    assert restored == result


def test_incomplete_partition_is_rejected() -> None:
    result = make_result()
    metadata = product_classification_metadata_to_item(result)
    with pytest.raises(ProductClassificationSerializationError):
        product_classification_result_from_items([metadata])
