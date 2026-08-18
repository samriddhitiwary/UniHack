from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from app.core.exceptions import (
    AttributeSelectionRepositoryError,
    AttributeSelectionResultAlreadyExistsError,
    AttributeSelectionResultItemTooLargeError,
)
from app.repositories import dynamodb_attribute_selection as module
from app.repositories.dynamodb_attribute_selection import DynamoDBAttributeSelectionResultRepository
from tests.unit.test_attribute_selection_engine import pipeline


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


def fixture():
    *_, result = pipeline(("ratedPower", "5.5", "kW"), ("ratedPower", "5.5", "kW"))
    return result


def test_round_trip_pagination_and_job_index() -> None:
    result, client = fixture(), Client()
    repository = DynamoDBAttributeSelectionResultRepository(client, "results")
    assert repository.create(result) is result
    assert repository.get_by_id(result.selection_id) == result
    assert repository.get_by_job_id(result.job_id) == result
    assert all(
        request.get("ConsistentRead") is True
        for request in client.requests
        if not request.get("IndexName")
    )


def test_missing_duplicate_malformed_failure_and_size_are_controlled(monkeypatch) -> None:
    result = fixture()
    empty = Client()
    empty.query = lambda **request: {"Items": []}
    repository = DynamoDBAttributeSelectionResultRepository(empty, "results")
    assert repository.get_by_id(uuid4()) is None and repository.get_by_job_id(uuid4()) is None

    class Failing(Client):
        def __init__(self, code):
            super().__init__()
            self.code = code

        def put_item(self, **request):
            raise ClientError({"Error": {"Code": self.code}}, "PutItem")

    with pytest.raises(AttributeSelectionResultAlreadyExistsError):
        DynamoDBAttributeSelectionResultRepository(
            Failing("ConditionalCheckFailedException"), "x"
        ).create(result)
    with pytest.raises(AttributeSelectionRepositoryError):
        DynamoDBAttributeSelectionResultRepository(Failing("InternalServerError"), "x").create(
            result
        )
    client = Client()
    repository = DynamoDBAttributeSelectionResultRepository(client, "x")
    repository.create(result)
    client.items = client.items[:1]
    with pytest.raises(AttributeSelectionRepositoryError):
        repository.get_by_id(result.selection_id)
    monkeypatch.setattr(module, "MAX_SAFE_ITEM_BYTES", 1)
    with pytest.raises(AttributeSelectionResultItemTooLargeError):
        DynamoDBAttributeSelectionResultRepository(Client(), "x").create(result)
