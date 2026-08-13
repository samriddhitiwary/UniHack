from uuid import uuid4

from app.domain.category_schemas.builtins import induction_motor_schema_v1
from app.repositories.dynamodb_attribute_normalization import (
    DynamoDBAttributeNormalizationResultRepository,
)
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
            return {"Items": [self.items[0]]}
        if request.get("ExclusiveStartKey"):
            return {"Items": self.items[1:]}
        if len(self.items) > 1:
            return {"Items": [self.items[0]], "LastEvaluatedKey": {"next": {"S": "yes"}}}
        return {"Items": self.items}


def test_composite_repository_round_trip_paginates_and_supports_job_index() -> None:
    schema = induction_motor_schema_v1()
    source = candidate(schema, "ratedPower", "5500", "W")
    result = AttributeNormalizationEngine().normalize(
        job_id=uuid4(), extraction_result=extraction(schema, (source,)), schema=schema, now=NOW
    )
    client = Client()
    repository = DynamoDBAttributeNormalizationResultRepository(client, "results")
    assert repository.create(result) is result
    assert len(client.items) == 2
    assert repository.get_by_id(result.normalization_id) == result
    assert repository.get_by_job_id(result.job_id) == result
    assert all(
        request.get("ConsistentRead") is True
        for request in client.requests
        if not request.get("IndexName")
    )
