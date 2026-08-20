"""Catalog enrichment DynamoDB repository access-pattern tests."""

from dataclasses import replace
from typing import Any, cast
from uuid import uuid4

import pytest
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from app.core.exceptions import (
    CatalogEnrichmentAlreadyExistsError,
    CatalogEnrichmentRepositoryError,
    CatalogEnrichmentResultItemTooLargeError,
    CatalogEnrichmentResultSerializationError,
)
from app.repositories.dynamodb_catalog_enrichment import (
    DynamoDBCatalogEnrichmentResultRepository,
)
from app.utils.dynamodb import deserialize_item
from tests.fixtures.catalog_enrichment import FakeLlm, enrichment_projection, grounded_response
from tests.unit.test_catalog_enrichment_engine import engine, generate


class MemoryDynamo:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], dict[str, Any]] = {}
        self.calls: list[str] = []
        self.failure = False

    def transact_write_items(self, *, TransactItems):
        self.calls.append("transact_write_items")
        if self.failure:
            raise ClientError({"Error": {"Code": "InternalServerError"}}, "TransactWriteItems")
        decoded = [deserialize_item(item["Put"]["Item"]) for item in TransactItems]
        decoded_keys = [(str(item["enrichmentId"]), str(item["recordKey"])) for item in decoded]
        if any(key in self.items for key in decoded_keys):
            raise ClientError(
                {"Error": {"Code": "TransactionCanceledException"}}, "TransactWriteItems"
            )
        for raw, item in zip(TransactItems, decoded, strict=True):
            self.items[(str(item["enrichmentId"]), str(item["recordKey"]))] = raw["Put"]["Item"]
        return {}

    def put_item(self, *, Item, **kwargs):
        self.calls.append("put_item")
        item = deserialize_item(Item)
        key = (str(item["enrichmentId"]), str(item["recordKey"]))
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
            return {"Items": matching[: request["Limit"]]}
        matching = [item for (partition, _), item in self.items.items() if partition == wanted]
        return {"Items": matching}


def fixture_result():
    _, _, projection = enrichment_projection()
    return generate(engine(FakeLlm([grounded_response(projection)])), projection)


def repository(client: MemoryDynamo) -> DynamoDBCatalogEnrichmentResultRepository:
    return DynamoDBCatalogEnrichmentResultRepository(cast(BaseClient, client), "enrichments")


def test_conditional_create_and_query_access_patterns_round_trip() -> None:
    result = fixture_result()
    client = MemoryDynamo()
    subject = repository(client)
    assert subject.create(result) == result
    assert subject.get_by_id(result.enrichment_id) == result
    assert subject.get_by_job_id(result.job_id) == result
    assert subject.get_by_projection_id(result.projection_id) == (result,)
    assert "scan" not in client.calls


def test_duplicate_id_and_exact_input_guard_are_rejected() -> None:
    result = fixture_result()
    client = MemoryDynamo()
    subject = repository(client)
    subject.create(result)
    with pytest.raises(CatalogEnrichmentAlreadyExistsError):
        subject.create(result)
    with pytest.raises(CatalogEnrichmentAlreadyExistsError):
        subject.create(replace(result, enrichment_id=uuid4(), job_id=uuid4()))


def test_incomplete_partition_and_repository_failure_are_controlled() -> None:
    result = fixture_result()
    client = MemoryDynamo()
    subject = repository(client)
    assert subject.get_by_id(result.enrichment_id) is None
    subject.create(result)
    del client.items[(str(result.enrichment_id), "TITLE")]
    with pytest.raises(CatalogEnrichmentResultSerializationError):
        subject.get_by_id(result.enrichment_id)
    failed = MemoryDynamo()
    failed.failure = True
    with pytest.raises(CatalogEnrichmentRepositoryError):
        repository(failed).create(result)


def test_item_size_guard_rejects_oversized_records() -> None:
    with pytest.raises(CatalogEnrichmentResultItemTooLargeError):
        DynamoDBCatalogEnrichmentResultRepository._guard_size({"value": "x" * 400_000})
