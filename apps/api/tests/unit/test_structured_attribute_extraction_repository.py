from datetime import UTC, datetime
from uuid import UUID

from app.domain.attribute_extraction import StructuredAttributeExtractionResult
from app.domain.category_schemas.builtins import induction_motor_schema_v1
from app.domain.products import ProductCategory
from app.repositories.dynamodb_structured_attribute_extraction import (
    DynamoDBStructuredAttributeExtractionResultRepository,
)


class Client:
    def __init__(self) -> None:
        self.items = []
        self.query_calls = []

    def put_item(self, **request):
        self.items.append(request["Item"])

    def query(self, **request):
        self.query_calls.append(request)
        if request.get("IndexName"):
            return {"Items": [self.items[0]]}
        start = 1 if request.get("ExclusiveStartKey") else 0
        response = {"Items": self.items[start : start + 1]}
        if start + 1 < len(self.items):
            response["LastEvaluatedKey"] = {"next": {"S": "yes"}}
        return response


def result() -> StructuredAttributeExtractionResult:
    return StructuredAttributeExtractionResult.create(
        job_id=UUID("11111111-1111-4111-8111-111111111111"),
        product_id=UUID("22222222-2222-4222-8222-222222222222"),
        classification_id=UUID("33333333-3333-4333-8333-333333333333"),
        category=ProductCategory.INDUCTION_MOTOR,
        schema_version=1,
        schema_fingerprint=induction_motor_schema_v1().schema_fingerprint,
        evidence_item_count=0,
        candidates=(),
        duplicate_count=0,
        warning_codes=(),
        now=datetime(2026, 8, 13, tzinfo=UTC),
    )


def test_composite_repository_creates_and_retrieves_by_id_and_job() -> None:
    client = Client()
    repository = DynamoDBStructuredAttributeExtractionResultRepository(client, "results")
    expected = result()
    assert repository.create(expected) is expected
    assert repository.get_by_id(expected.extraction_id) == expected
    assert repository.get_by_job_id(expected.job_id) == expected
    assert all(
        call.get("ConsistentRead") is True
        for call in client.query_calls
        if not call.get("IndexName")
    )
