"""Catalog enrichment record and schema serialization tests."""

import pytest

from app.core.exceptions import CatalogEnrichmentResultSerializationError
from app.repositories.dynamodb_catalog_enrichment import (
    DynamoDBCatalogEnrichmentResultRepository,
)
from app.schemas.catalog_enrichment import CatalogEnrichmentResultRecord
from app.utils.dynamodb import deserialize_item, serialize_item
from tests.unit.test_catalog_enrichment_repository import fixture_result


def test_meta_content_records_round_trip_and_schema_is_camel_case() -> None:
    result = fixture_result()
    logical = [DynamoDBCatalogEnrichmentResultRepository._meta(result)]
    logical.extend(DynamoDBCatalogEnrichmentResultRepository._content_records(result))
    items = [deserialize_item(serialize_item(item)) for item in logical]
    assert DynamoDBCatalogEnrichmentResultRepository._from_items(items) == result
    body = CatalogEnrichmentResultRecord.model_validate(result).model_dump(
        by_alias=True, mode="json"
    )
    assert body["enrichmentId"] == str(result.enrichment_id)
    assert body["title"]["factIds"]


def test_missing_meta_or_content_is_rejected() -> None:
    result = fixture_result()
    logical = [DynamoDBCatalogEnrichmentResultRepository._meta(result)]
    logical.extend(DynamoDBCatalogEnrichmentResultRepository._content_records(result))
    items = [deserialize_item(serialize_item(item)) for item in logical]
    with pytest.raises(CatalogEnrichmentResultSerializationError):
        DynamoDBCatalogEnrichmentResultRepository._from_items(items[1:])
    with pytest.raises(CatalogEnrichmentResultSerializationError):
        DynamoDBCatalogEnrichmentResultRepository._from_items(items[:-1])
