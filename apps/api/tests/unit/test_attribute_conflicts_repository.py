from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from app.core.exceptions import (
    AttributeConflictRepositoryError,
    AttributeConflictResultAlreadyExistsError,
    AttributeConflictResultItemTooLargeError,
)
from app.domain.category_schemas.builtins import induction_motor_schema_v1
from app.repositories import dynamodb_attribute_conflicts as module
from app.repositories.dynamodb_attribute_conflicts import (
    DynamoDBAttributeConflictDetectionResultRepository,
)
from app.services.attribute_conflict_detection_engine import AttributeConflictDetectionEngine
from app.services.attribute_normalization_engine import AttributeNormalizationEngine
from tests.fixtures.attribute_normalization import NOW, candidate, extraction


class Client:
    def __init__(self) -> None:
        self.items = []
        self.requests = []

    def put_item(self, **request):
        self.items.append(request["Item"])

    def query(self, **request):
        self.requests.append(request)
        if request.get("IndexName"):
            return {"Items": [self.items[0]]} if self.items else {"Items": []}
        if request.get("ExclusiveStartKey"):
            return {"Items": self.items[1:]}
        if len(self.items) > 1:
            return {"Items": [self.items[0]], "LastEvaluatedKey": {"next": {"S": "yes"}}}
        return {"Items": self.items}


def result_fixture():
    schema = induction_motor_schema_v1()
    normalized = AttributeNormalizationEngine().normalize(
        job_id=uuid4(),
        extraction_result=extraction(
            schema,
            (
                candidate(schema, "voltage", "415", "V", index=1),
                candidate(schema, "voltage", "440", "V", index=2),
            ),
        ),
        schema=schema,
        now=NOW,
    )
    return AttributeConflictDetectionEngine().detect(
        job_id=uuid4(), normalization_result=normalized, now=NOW
    )


def test_composite_round_trip_paginates_and_uses_job_index_without_scan() -> None:
    result = result_fixture()
    client = Client()
    repository = DynamoDBAttributeConflictDetectionResultRepository(client, "results")
    assert repository.create(result) is result
    assert len(client.items) == 4
    assert repository.get_by_id(result.conflict_detection_id) == result
    assert repository.get_by_job_id(result.job_id) == result
    assert all(
        request.get("ConsistentRead") is True
        for request in client.requests
        if not request.get("IndexName")
    )
    assert not any("Scan" in request for request in client.requests)


def test_missing_results_return_none() -> None:
    repository = DynamoDBAttributeConflictDetectionResultRepository(Client(), "results")
    assert repository.get_by_id(uuid4()) is None
    assert repository.get_by_job_id(uuid4()) is None


def test_duplicate_and_client_failures_are_controlled() -> None:
    result = result_fixture()

    class FailingClient(Client):
        def __init__(self, code):
            super().__init__()
            self.code = code

        def put_item(self, **request):
            raise ClientError({"Error": {"Code": self.code}}, "PutItem")

    duplicate = DynamoDBAttributeConflictDetectionResultRepository(
        FailingClient("ConditionalCheckFailedException"), "results"
    )
    with pytest.raises(AttributeConflictResultAlreadyExistsError):
        duplicate.create(result)
    failure = DynamoDBAttributeConflictDetectionResultRepository(
        FailingClient("InternalServerError"), "results"
    )
    with pytest.raises(AttributeConflictRepositoryError):
        failure.create(result)


def test_malformed_partition_and_oversized_item_are_controlled(monkeypatch) -> None:
    result = result_fixture()
    client = Client()
    repository = DynamoDBAttributeConflictDetectionResultRepository(client, "results")
    repository.create(result)
    client.items = client.items[:1]
    with pytest.raises(AttributeConflictRepositoryError):
        repository.get_by_id(result.conflict_detection_id)

    monkeypatch.setattr(module, "MAX_SAFE_ITEM_BYTES", 1)
    with pytest.raises(AttributeConflictResultItemTooLargeError):
        DynamoDBAttributeConflictDetectionResultRepository(Client(), "results").create(result)
