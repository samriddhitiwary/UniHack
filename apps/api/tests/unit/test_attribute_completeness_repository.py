from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from app.core.exceptions import (
    AttributeCompletenessRepositoryError,
    AttributeCompletenessResultAlreadyExistsError,
    AttributeCompletenessResultItemTooLargeError,
)
from app.repositories import dynamodb_attribute_completeness as module
from app.repositories.dynamodb_attribute_completeness import (
    DynamoDBAttributeCompletenessResultRepository,
)
from app.services.attribute_completeness_engine import AttributeCompletenessEngine
from tests.fixtures.attribute_normalization import NOW
from tests.unit.test_attribute_completeness_engine import conflict_for


class Client:
    def __init__(self):
        self.items, self.requests = [], []

    def put_item(self, **request):
        self.items.append(request["Item"])

    def query(self, **request):
        self.requests.append(request)
        if request.get("IndexName"):
            return {"Items": self.items[:1]}
        if request.get("ExclusiveStartKey"):
            return {"Items": self.items[1:]}
        return {"Items": self.items[:1], "LastEvaluatedKey": {"next": {"S": "yes"}}}


def test_composite_round_trip_pagination_and_job_index() -> None:
    schema, conflict = conflict_for(("voltage", "415", "V"))
    result = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(), conflict_result=conflict, schema=schema, now=NOW
    )
    client = Client()
    repository = DynamoDBAttributeCompletenessResultRepository(client, "results")
    assert repository.create(result) is result
    assert repository.get_by_id(result.completeness_id) == result
    assert repository.get_by_job_id(result.job_id) == result
    assert all(
        request.get("ConsistentRead") is True
        for request in client.requests
        if not request.get("IndexName")
    )


def test_missing_results_return_none() -> None:
    client = Client()
    client.query = lambda **request: {"Items": []}
    repository = DynamoDBAttributeCompletenessResultRepository(client, "results")
    assert repository.get_by_id(uuid4()) is None
    assert repository.get_by_job_id(uuid4()) is None


def test_duplicate_client_failure_malformed_and_oversized_are_controlled(monkeypatch) -> None:
    schema, conflict = conflict_for(("voltage", "415", "V"))
    result = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(), conflict_result=conflict, schema=schema, now=NOW
    )

    class FailingClient(Client):
        def __init__(self, code):
            super().__init__()
            self.code = code

        def put_item(self, **request):
            raise ClientError({"Error": {"Code": self.code}}, "PutItem")

    with pytest.raises(AttributeCompletenessResultAlreadyExistsError):
        DynamoDBAttributeCompletenessResultRepository(
            FailingClient("ConditionalCheckFailedException"), "results"
        ).create(result)
    with pytest.raises(AttributeCompletenessRepositoryError):
        DynamoDBAttributeCompletenessResultRepository(
            FailingClient("InternalServerError"), "results"
        ).create(result)

    client = Client()
    repository = DynamoDBAttributeCompletenessResultRepository(client, "results")
    repository.create(result)
    client.items = client.items[:1]
    with pytest.raises(AttributeCompletenessRepositoryError):
        repository.get_by_id(result.completeness_id)

    monkeypatch.setattr(module, "MAX_SAFE_ITEM_BYTES", 1)
    with pytest.raises(AttributeCompletenessResultItemTooLargeError):
        DynamoDBAttributeCompletenessResultRepository(Client(), "results").create(result)
