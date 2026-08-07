"""DynamoDB PDF extraction result repository request-contract tests."""

import boto3
import pytest
from botocore.client import BaseClient
from botocore.stub import Stubber

from app.core.exceptions import (
    PdfExtractionRepositoryError,
    PdfExtractionResultAlreadyExistsError,
    PdfExtractionSerializationError,
)
from app.repositories.dynamodb_pdf_extraction import (
    JOB_ID_INDEX,
    DynamoDBPdfExtractionResultRepository,
)
from app.utils.dynamodb import (
    pdf_extraction_metadata_to_item,
    pdf_extraction_page_to_item,
    serialize_item,
)
from tests.fixtures.pdf_extraction import EXTRACTION_ID, make_pdf_extraction_result
from tests.fixtures.processing_jobs import JOB_ID

TABLE_NAME = "catalogiq-test-extraction-results"


@pytest.fixture
def dynamodb_client() -> BaseClient:
    return boto3.client(
        "dynamodb",
        region_name="ap-south-1",
        endpoint_url="http://localhost:8001",
        aws_access_key_id="local",
        aws_secret_access_key="local",
    )


def test_create_conditionally_writes_metadata_then_page_records(
    dynamodb_client: BaseClient,
) -> None:
    result = make_pdf_extraction_result()
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response("put_item", {}, _metadata_put(result))
        for page in result.pages:
            stubber.add_response("put_item", {}, _page_put(result, page.page_number))
        repository = DynamoDBPdfExtractionResultRepository(dynamodb_client, TABLE_NAME)
        assert repository.create(result) == result


def test_duplicate_create_is_controlled(dynamodb_client: BaseClient) -> None:
    result = make_pdf_extraction_result()
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "put_item",
            service_error_code="ConditionalCheckFailedException",
            expected_params=_metadata_put(result),
        )
        with pytest.raises(PdfExtractionResultAlreadyExistsError):
            DynamoDBPdfExtractionResultRepository(dynamodb_client, TABLE_NAME).create(result)


def test_get_by_id_reconstructs_ordered_result_across_query_pages(
    dynamodb_client: BaseClient,
) -> None:
    result = make_pdf_extraction_result()
    metadata = serialize_item(pdf_extraction_metadata_to_item(result))
    page_items = [
        serialize_item(pdf_extraction_page_to_item(result.extraction_id, page))
        for page in result.pages
    ]
    last_key = serialize_item({"extractionId": EXTRACTION_ID, "recordKey": "PAGE#000001"})
    request = _id_query(EXTRACTION_ID)
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response(
            "query", {"Items": [metadata, page_items[0]], "LastEvaluatedKey": last_key}, request
        )
        stubber.add_response(
            "query", {"Items": [page_items[1]]}, {**request, "ExclusiveStartKey": last_key}
        )
        restored = DynamoDBPdfExtractionResultRepository(dynamodb_client, TABLE_NAME).get_by_id(
            EXTRACTION_ID
        )
    assert restored == result


def test_get_by_id_missing_returns_none(dynamodb_client: BaseClient) -> None:
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response("query", {"Items": []}, _id_query(EXTRACTION_ID))
        assert (
            DynamoDBPdfExtractionResultRepository(dynamodb_client, TABLE_NAME).get_by_id(
                EXTRACTION_ID
            )
            is None
        )


def test_get_by_job_uses_sparse_index_then_retrieves_pages(dynamodb_client: BaseClient) -> None:
    result = make_pdf_extraction_result()
    metadata = serialize_item(pdf_extraction_metadata_to_item(result))
    all_items = [metadata] + [
        serialize_item(pdf_extraction_page_to_item(result.extraction_id, page))
        for page in result.pages
    ]
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response("query", {"Items": [metadata]}, _job_query(JOB_ID))
        stubber.add_response("query", {"Items": all_items}, _id_query(EXTRACTION_ID))
        restored = DynamoDBPdfExtractionResultRepository(dynamodb_client, TABLE_NAME).get_by_job_id(
            JOB_ID
        )
    assert restored == result


def test_get_by_job_missing_returns_none(dynamodb_client: BaseClient) -> None:
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response("query", {"Items": []}, _job_query(JOB_ID))
        assert (
            DynamoDBPdfExtractionResultRepository(dynamodb_client, TABLE_NAME).get_by_job_id(JOB_ID)
            is None
        )


def test_malformed_result_and_repository_errors_are_controlled(
    dynamodb_client: BaseClient,
) -> None:
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response(
            "query",
            {"Items": [serialize_item({"extractionId": EXTRACTION_ID, "recordKey": "META"})]},
            _id_query(EXTRACTION_ID),
        )
        with pytest.raises(PdfExtractionSerializationError):
            DynamoDBPdfExtractionResultRepository(dynamodb_client, TABLE_NAME).get_by_id(
                EXTRACTION_ID
            )

    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "query",
            service_error_code="InternalServerError",
            expected_params=_id_query(EXTRACTION_ID),
        )
        with pytest.raises(PdfExtractionRepositoryError):
            DynamoDBPdfExtractionResultRepository(dynamodb_client, TABLE_NAME).get_by_id(
                EXTRACTION_ID
            )


def test_page_write_failure_is_safe_repository_error(dynamodb_client: BaseClient) -> None:
    result = make_pdf_extraction_result()
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response("put_item", {}, _metadata_put(result))
        stubber.add_client_error(
            "put_item",
            service_error_code="InternalServerError",
            expected_params=_page_put(result, 1),
        )
        with pytest.raises(PdfExtractionRepositoryError):
            DynamoDBPdfExtractionResultRepository(dynamodb_client, TABLE_NAME).create(result)


def _metadata_put(result: object) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "Item": serialize_item(pdf_extraction_metadata_to_item(result)),  # type: ignore[arg-type]
        "ConditionExpression": "attribute_not_exists(#extractionId)",
        "ExpressionAttributeNames": {"#extractionId": "extractionId"},
    }


def _page_put(result: object, page_number: int) -> dict[str, object]:
    page = result.pages[page_number - 1]  # type: ignore[attr-defined]
    return {
        "TableName": TABLE_NAME,
        "Item": serialize_item(pdf_extraction_page_to_item(result.extraction_id, page)),  # type: ignore[attr-defined]
        "ConditionExpression": "attribute_not_exists(#recordKey)",
        "ExpressionAttributeNames": {"#recordKey": "recordKey"},
    }


def _id_query(extraction_id: object) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "KeyConditionExpression": "#extractionId = :extractionId",
        "ExpressionAttributeNames": {"#extractionId": "extractionId"},
        "ExpressionAttributeValues": serialize_item({":extractionId": extraction_id}),
        "ConsistentRead": True,
    }


def _job_query(job_id: object) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "IndexName": JOB_ID_INDEX,
        "KeyConditionExpression": "#jobId = :jobId",
        "ExpressionAttributeNames": {"#jobId": "jobId"},
        "ExpressionAttributeValues": serialize_item({":jobId": job_id}),
        "ScanIndexForward": False,
        "Limit": 1,
    }
