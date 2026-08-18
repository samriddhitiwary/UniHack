"""Catalog export schema and DynamoDB record serialization tests."""

import pytest

from app.core.exceptions import CatalogExportResultSerializationError
from app.repositories.dynamodb_catalog_export import DynamoDBCatalogExportResultRepository
from app.schemas.catalog_export import CatalogExportResultRecord
from app.utils.dynamodb import deserialize_item, serialize_item
from tests.fixtures.catalog_export import export_result


def test_result_schema_serializes_camel_case_enums_checksums_and_lineage() -> None:
    _, _, _, result = export_result(manufacturer=None)
    body = CatalogExportResultRecord.model_validate(result).model_dump(by_alias=True, mode="json")
    assert body["exportId"] == str(result.export_id)
    assert body["projectionProductVersion"] == 3
    assert body["projectionStatus"] == "READY_WITH_WARNINGS"
    assert body["warningReasonCodes"] == ["MANUFACTURER_MISSING"]
    assert body["artifacts"][0]["format"] == "CANONICAL_JSON"
    assert len(body["artifacts"][0]["sha256"]) == 64


def test_meta_and_artifact_records_round_trip() -> None:
    _, _, _, result = export_result()
    logical_items = [DynamoDBCatalogExportResultRepository._meta(result)] + [
        DynamoDBCatalogExportResultRepository._artifact(result.export_id, artifact)
        for artifact in result.artifacts
    ]
    items = [deserialize_item(serialize_item(item)) for item in logical_items]
    assert DynamoDBCatalogExportResultRepository._from_items(items) == result


def test_incomplete_or_malformed_records_are_rejected() -> None:
    _, _, _, result = export_result()
    logical_items = [DynamoDBCatalogExportResultRepository._meta(result)] + [
        DynamoDBCatalogExportResultRepository._artifact(result.export_id, artifact)
        for artifact in result.artifacts
    ]
    items = [deserialize_item(serialize_item(item)) for item in logical_items]
    with pytest.raises(CatalogExportResultSerializationError):
        DynamoDBCatalogExportResultRepository._from_items(items[1:])
    with pytest.raises(CatalogExportResultSerializationError):
        DynamoDBCatalogExportResultRepository._from_items(items[:-1])
    malformed = [items[0], replace_dict(items[1], sha256="bad"), *items[2:]]
    with pytest.raises(CatalogExportResultSerializationError):
        DynamoDBCatalogExportResultRepository._from_items(malformed)


def replace_dict(value: dict[str, object], **changes: object) -> dict[str, object]:
    return {**value, **changes}
