"""Catalog export DynamoDB repository access-pattern tests."""

from dataclasses import replace
from typing import Any, cast
from uuid import uuid4

import pytest
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from app.core.exceptions import (
    CatalogExportAlreadyExistsError,
    CatalogExportRepositoryError,
    CatalogExportResultItemTooLargeError,
    CatalogExportResultSerializationError,
)
from app.repositories.dynamodb_catalog_export import DynamoDBCatalogExportResultRepository
from app.utils.dynamodb import deserialize_item
from tests.fixtures.catalog_export import export_result


class MemoryDynamo:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], dict[str, Any]] = {}
        self.calls: list[str] = []
        self.failure: str | None = None

    def transact_write_items(self, *, TransactItems):
        self.calls.append("transact_write_items")
        if self.failure == "storage":
            raise ClientError({"Error": {"Code": "InternalServerError"}}, "TransactWriteItems")
        decoded = [deserialize_item(item["Put"]["Item"]) for item in TransactItems]
        if any((str(item["exportId"]), str(item["recordKey"])) in self.items for item in decoded):
            raise ClientError(
                {"Error": {"Code": "TransactionCanceledException"}}, "TransactWriteItems"
            )
        for raw, item in zip(TransactItems, decoded, strict=True):
            self.items[(str(item["exportId"]), str(item["recordKey"]))] = raw["Put"]["Item"]
        return {}

    def put_item(self, *, Item, **kwargs):
        self.calls.append("put_item")
        item = deserialize_item(Item)
        key = (str(item["exportId"]), str(item["recordKey"]))
        if key in self.items:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
        self.items[key] = Item
        return {}

    def query(self, **request):
        self.calls.append("query")
        values = deserialize_item(request["ExpressionAttributeValues"])
        wanted = str(next(iter(values.values())))
        if "IndexName" in request:
            field = "jobId" if request["IndexName"] == "JobIdIndex" else "projectionId"
            matching = [
                item
                for item in self.items.values()
                if str(deserialize_item(item).get(field, "")) == wanted
            ]
            return {"Items": matching[:1]}
        return {
            "Items": [item for (partition, _), item in self.items.items() if partition == wanted]
        }


def _repository(client: MemoryDynamo) -> DynamoDBCatalogExportResultRepository:
    return DynamoDBCatalogExportResultRepository(cast(BaseClient, client), "exports")


def test_conditional_create_and_all_query_access_patterns_round_trip() -> None:
    _, _, _, result = export_result()
    client = MemoryDynamo()
    repository = _repository(client)
    assert repository.create(result) == result
    assert repository.get_by_id(result.export_id) == result
    assert repository.get_by_job_id(result.job_id) == result
    assert repository.get_by_projection_id(result.projection_id) == result
    assert "scan" not in client.calls


def test_duplicate_export_id_and_projection_guard_are_rejected() -> None:
    _, _, _, result = export_result()
    client = MemoryDynamo()
    repository = _repository(client)
    repository.create(result)
    with pytest.raises(CatalogExportAlreadyExistsError):
        repository.create(result)
    other_id = uuid4()
    other = replace(
        result,
        export_id=other_id,
        artifacts=tuple(
            replace(
                artifact,
                object_key=f"catalog-exports/{other_id}/{artifact.file_name}",
            )
            for artifact in result.artifacts
        ),
    )
    with pytest.raises(CatalogExportAlreadyExistsError):
        repository.create(other)


def test_missing_and_incomplete_partitions_are_detected() -> None:
    _, _, _, result = export_result()
    client = MemoryDynamo()
    repository = _repository(client)
    assert repository.get_by_id(result.export_id) is None
    repository.create(result)
    del client.items[(str(result.export_id), "ARTIFACT#MANIFEST_JSON")]
    with pytest.raises(CatalogExportResultSerializationError):
        repository.get_by_id(result.export_id)


def test_storage_failure_is_safely_wrapped() -> None:
    _, _, _, result = export_result()
    client = MemoryDynamo()
    client.failure = "storage"
    with pytest.raises(CatalogExportRepositoryError):
        _repository(client).create(result)


def test_item_size_guard_rejects_oversized_record() -> None:
    with pytest.raises(CatalogExportResultItemTooLargeError):
        DynamoDBCatalogExportResultRepository._guard_size({"value": "x" * 400_000})
