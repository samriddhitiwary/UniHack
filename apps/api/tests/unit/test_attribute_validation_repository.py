from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from app.core.exceptions import (
    AttributeValidationRepositoryError,
    AttributeValidationResultAlreadyExistsError,
    AttributeValidationResultItemTooLargeError,
)
from app.repositories import dynamodb_attribute_validation as module
from app.repositories.dynamodb_attribute_validation import (
    DynamoDBAttributeValidationResultRepository,
)
from app.services.attribute_validation_engine import AttributeValidationEngine
from tests.fixtures.attribute_normalization import NOW
from tests.unit.test_attribute_validation_engine import normalized


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


def result_fixture():
    schema, normalization = normalized(("voltage", "415", "V"), ("voltage", "440", "V"))
    return AttributeValidationEngine().validate(
        job_id=uuid4(), normalization_result=normalization, schema=schema, now=NOW
    )


def test_composite_round_trip_pagination_order_and_job_index() -> None:
    result = result_fixture()
    client = Client()
    repository = DynamoDBAttributeValidationResultRepository(client, "results")
    assert repository.create(result) is result
    assert repository.get_by_id(result.validation_id) == result
    assert repository.get_by_job_id(result.job_id) == result
    assert all(
        request.get("ConsistentRead") is True
        for request in client.requests
        if not request.get("IndexName")
    )


def test_missing_duplicate_malformed_client_and_oversized_are_controlled(monkeypatch) -> None:
    result = result_fixture()
    empty = Client()
    empty.query = lambda **request: {"Items": []}
    repository = DynamoDBAttributeValidationResultRepository(empty, "results")
    assert repository.get_by_id(uuid4()) is None and repository.get_by_job_id(uuid4()) is None

    class FailingClient(Client):
        def __init__(self, code):
            super().__init__()
            self.code = code

        def put_item(self, **request):
            raise ClientError({"Error": {"Code": self.code}}, "PutItem")

    with pytest.raises(AttributeValidationResultAlreadyExistsError):
        DynamoDBAttributeValidationResultRepository(
            FailingClient("ConditionalCheckFailedException"), "results"
        ).create(result)
    with pytest.raises(AttributeValidationRepositoryError):
        DynamoDBAttributeValidationResultRepository(
            FailingClient("InternalServerError"), "results"
        ).create(result)
    client = Client()
    repository = DynamoDBAttributeValidationResultRepository(client, "results")
    repository.create(result)
    client.items = client.items[:1]
    with pytest.raises(AttributeValidationRepositoryError):
        repository.get_by_id(result.validation_id)
    monkeypatch.setattr(module, "MAX_SAFE_ITEM_BYTES", 1)
    with pytest.raises(AttributeValidationResultItemTooLargeError):
        DynamoDBAttributeValidationResultRepository(Client(), "results").create(result)
