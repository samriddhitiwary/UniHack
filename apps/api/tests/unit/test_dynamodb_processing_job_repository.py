"""DynamoDB processing-job repository request-contract tests."""

from dataclasses import replace
from uuid import uuid4

import boto3
import pytest
from botocore.client import BaseClient
from botocore.stub import Stubber

from app.core.exceptions import (
    InvalidProcessingJobCursorError,
    ProcessingJobAlreadyExistsError,
    ProcessingJobNotFoundError,
    ProcessingJobRepositoryError,
    ProcessingJobVersionConflictError,
)
from app.domain.processing_jobs import ProcessingJobStatus, transition_processing_job
from app.repositories.dynamodb_processing_jobs import (
    PRODUCT_CREATED_AT_INDEX,
    SOURCE_CREATED_AT_INDEX,
    DynamoDBProcessingJobRepository,
)
from app.utils.cursors import (
    encode_processing_job_product_cursor,
    encode_processing_job_source_cursor,
)
from app.utils.dynamodb import (
    processing_job_source_scope,
    processing_job_to_item,
    serialize_item,
)
from tests.fixtures.processing_jobs import (
    JOB_CREATED_AT,
    JOB_ID,
    JOB_STARTED_AT,
    JOB_UPDATED_AT,
    SECOND_JOB_ID,
    make_processing_job,
)
from tests.fixtures.product_sources import SOURCE_ID
from tests.fixtures.products import PRODUCT_ID

TABLE_NAME = "catalogiq-test-processing-jobs"


@pytest.fixture
def dynamodb_client() -> BaseClient:
    return boto3.client(
        "dynamodb",
        region_name="ap-south-1",
        endpoint_url="http://localhost:8001",
        aws_access_key_id="local",
        aws_secret_access_key="local",
    )


def test_create_is_conditional_and_duplicate_is_controlled(dynamodb_client: BaseClient) -> None:
    job = make_processing_job()
    request = _create_request(job)
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response("put_item", {}, request)
        stubber.add_client_error(
            "put_item",
            service_error_code="ConditionalCheckFailedException",
            expected_params=request,
        )
        repository = DynamoDBProcessingJobRepository(dynamodb_client, TABLE_NAME)
        assert repository.create(job) == job
        with pytest.raises(ProcessingJobAlreadyExistsError):
            repository.create(job)


def test_get_and_missing(dynamodb_client: BaseClient) -> None:
    job = make_processing_job()
    request = _get_request(JOB_ID)
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response(
            "get_item", {"Item": serialize_item(processing_job_to_item(job))}, request
        )
        stubber.add_response("get_item", {}, request)
        repository = DynamoDBProcessingJobRepository(dynamodb_client, TABLE_NAME)
        assert repository.get_by_id(JOB_ID) == job
        assert repository.get_by_id(JOB_ID) is None


def test_product_list_uses_gsi_descending_and_paginates(dynamodb_client: BaseClient) -> None:
    first = make_processing_job()
    second = make_processing_job(job_id=SECOND_JOB_ID)
    last_key = serialize_item(
        {"jobId": JOB_ID, "productId": PRODUCT_ID, "createdAt": JOB_CREATED_AT}
    )
    request = _product_query_request(limit=1)
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response(
            "query",
            {
                "Items": [serialize_item(processing_job_to_item(first))],
                "LastEvaluatedKey": last_key,
            },
            request,
        )
        stubber.add_response(
            "query",
            {"Items": [serialize_item(processing_job_to_item(second))]},
            {**request, "ExclusiveStartKey": last_key},
        )
        repository = DynamoDBProcessingJobRepository(dynamodb_client, TABLE_NAME)
        page = repository.list_by_product(PRODUCT_ID, limit=1)
        assert page.items == (first,)
        assert isinstance(page.next_cursor, str) and "jobId" not in page.next_cursor
        final = repository.list_by_product(PRODUCT_ID, limit=1, cursor=page.next_cursor)
        assert final.items == (second,) and final.next_cursor is None


def test_source_list_uses_scoped_gsi_descending_and_paginates(
    dynamodb_client: BaseClient,
) -> None:
    first = make_processing_job()
    last_key = serialize_item(
        {
            "jobId": JOB_ID,
            "sourceScope": processing_job_source_scope(PRODUCT_ID, SOURCE_ID),
            "createdAt": JOB_CREATED_AT,
        }
    )
    request = _source_query_request(limit=1)
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response(
            "query",
            {
                "Items": [serialize_item(processing_job_to_item(first))],
                "LastEvaluatedKey": last_key,
            },
            request,
        )
        repository = DynamoDBProcessingJobRepository(dynamodb_client, TABLE_NAME)
        page = repository.list_by_source(PRODUCT_ID, SOURCE_ID, limit=1)
    assert page.items == (first,) and page.next_cursor is not None


def test_cursor_scopes_limits_and_identities_are_rejected_without_query(
    dynamodb_client: BaseClient,
) -> None:
    repository = DynamoDBProcessingJobRepository(dynamodb_client, TABLE_NAME)
    with pytest.raises(ValueError):
        repository.list_by_product(PRODUCT_ID, limit=0)
    with pytest.raises(InvalidProcessingJobCursorError):
        repository.list_by_product(PRODUCT_ID, cursor="malformed")
    product_key = serialize_item(
        {"jobId": JOB_ID, "productId": PRODUCT_ID, "createdAt": JOB_CREATED_AT}
    )
    source_key = serialize_item(
        {
            "jobId": JOB_ID,
            "sourceScope": processing_job_source_scope(PRODUCT_ID, SOURCE_ID),
            "createdAt": JOB_CREATED_AT,
        }
    )
    other_product = uuid4()
    with pytest.raises(InvalidProcessingJobCursorError):
        repository.list_by_product(
            PRODUCT_ID, cursor=encode_processing_job_product_cursor(other_product, product_key)
        )
    with pytest.raises(InvalidProcessingJobCursorError):
        repository.list_by_source(
            PRODUCT_ID,
            SOURCE_ID,
            cursor=encode_processing_job_source_cursor(PRODUCT_ID, uuid4(), source_key),
        )
    with pytest.raises(InvalidProcessingJobCursorError):
        repository.list_by_source(
            PRODUCT_ID,
            SOURCE_ID,
            cursor=encode_processing_job_product_cursor(PRODUCT_ID, product_key),
        )
    with pytest.raises(InvalidProcessingJobCursorError):
        repository.list_by_product(
            PRODUCT_ID,
            cursor=encode_processing_job_source_cursor(PRODUCT_ID, SOURCE_ID, source_key),
        )


def test_update_is_conditional_increments_once_and_preserves_identity(
    dynamodb_client: BaseClient,
) -> None:
    current = make_processing_job()
    candidate = transition_processing_job(current, ProcessingJobStatus.RUNNING, now=JOB_STARTED_AT)
    expected = replace(candidate, updated_at=JOB_UPDATED_AT, version=2)
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response(
            "update_item",
            {"Attributes": serialize_item(processing_job_to_item(expected))},
            _update_request(candidate, expected_version=1),
        )
        repository = DynamoDBProcessingJobRepository(
            dynamodb_client, TABLE_NAME, clock=lambda: JOB_UPDATED_AT
        )
        updated = repository.update(candidate, expected_version=1)
    assert updated == expected
    assert (updated.job_id, updated.product_id, updated.source_id, updated.job_type) == (
        current.job_id,
        current.product_id,
        current.source_id,
        current.job_type,
    )
    assert updated.attempt == current.attempt and updated.created_at == current.created_at


@pytest.mark.parametrize("missing", [False, True])
def test_update_conditional_failure_distinguishes_stale_and_missing(
    dynamodb_client: BaseClient, missing: bool
) -> None:
    job = make_processing_job()
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "update_item",
            service_error_code="ConditionalCheckFailedException",
            expected_params=_update_request(job, expected_version=1),
        )
        response = {} if missing else {"Item": serialize_item(processing_job_to_item(job))}
        stubber.add_response("get_item", response, _get_request(JOB_ID))
        repository = DynamoDBProcessingJobRepository(
            dynamodb_client, TABLE_NAME, clock=lambda: JOB_UPDATED_AT
        )
        expected_error = (
            ProcessingJobNotFoundError if missing else ProcessingJobVersionConflictError
        )
        with pytest.raises(expected_error):
            repository.update(job, expected_version=1)


@pytest.mark.parametrize("operation", ["create", "get", "product_list", "source_list", "update"])
def test_repository_wraps_boto_failures(dynamodb_client: BaseClient, operation: str) -> None:
    job = make_processing_job()
    method, request = {
        "create": ("put_item", _create_request(job)),
        "get": ("get_item", _get_request(JOB_ID)),
        "product_list": ("query", _product_query_request(limit=25)),
        "source_list": ("query", _source_query_request(limit=25)),
        "update": ("update_item", _update_request(job, expected_version=1)),
    }[operation]
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            method, service_error_code="InternalServerError", expected_params=request
        )
        repository = DynamoDBProcessingJobRepository(
            dynamodb_client, TABLE_NAME, clock=lambda: JOB_UPDATED_AT
        )
        with pytest.raises(ProcessingJobRepositoryError):
            if operation == "create":
                repository.create(job)
            elif operation == "get":
                repository.get_by_id(JOB_ID)
            elif operation == "product_list":
                repository.list_by_product(PRODUCT_ID)
            elif operation == "source_list":
                repository.list_by_source(PRODUCT_ID, SOURCE_ID)
            else:
                repository.update(job, expected_version=1)


def _create_request(job: object) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "Item": serialize_item(processing_job_to_item(job)),  # type: ignore[arg-type]
        "ConditionExpression": "attribute_not_exists(#jobId)",
        "ExpressionAttributeNames": {"#jobId": "jobId"},
    }


def _get_request(job_id: object) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "Key": serialize_item({"jobId": job_id}),
        "ConsistentRead": True,
    }


def _product_query_request(*, limit: int) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "IndexName": PRODUCT_CREATED_AT_INDEX,
        "KeyConditionExpression": "#scope = :scope",
        "ExpressionAttributeNames": {"#scope": "productId"},
        "ExpressionAttributeValues": serialize_item({":scope": PRODUCT_ID}),
        "ScanIndexForward": False,
        "Limit": limit,
    }


def _source_query_request(*, limit: int) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "IndexName": SOURCE_CREATED_AT_INDEX,
        "KeyConditionExpression": "#scope = :scope",
        "ExpressionAttributeNames": {"#scope": "sourceScope"},
        "ExpressionAttributeValues": serialize_item(
            {":scope": processing_job_source_scope(PRODUCT_ID, SOURCE_ID)}
        ),
        "ScanIndexForward": False,
        "Limit": limit,
    }


def _update_request(job: object, *, expected_version: int) -> dict[str, object]:
    return {
        "TableName": TABLE_NAME,
        "Key": serialize_item({"jobId": job.job_id}),  # type: ignore[attr-defined]
        "UpdateExpression": (
            "SET #status = :status, #progressPercent = :progressPercent, "
            "#errorCode = :errorCode, #errorMessage = :errorMessage, "
            "#resultReference = :resultReference, #startedAt = :startedAt, "
            "#completedAt = :completedAt, #updatedAt = :updatedAt, #version = :newVersion"
        ),
        "ConditionExpression": "attribute_exists(#jobId) AND #version = :expectedVersion",
        "ExpressionAttributeNames": {
            "#jobId": "jobId",
            "#status": "status",
            "#progressPercent": "progressPercent",
            "#errorCode": "errorCode",
            "#errorMessage": "errorMessage",
            "#resultReference": "resultReference",
            "#startedAt": "startedAt",
            "#completedAt": "completedAt",
            "#updatedAt": "updatedAt",
            "#version": "version",
        },
        "ExpressionAttributeValues": serialize_item(
            {
                ":status": job.status,  # type: ignore[attr-defined]
                ":progressPercent": job.progress_percent,  # type: ignore[attr-defined]
                ":errorCode": job.error_code,  # type: ignore[attr-defined]
                ":errorMessage": job.error_message,  # type: ignore[attr-defined]
                ":resultReference": job.result_reference,  # type: ignore[attr-defined]
                ":startedAt": job.started_at,  # type: ignore[attr-defined]
                ":completedAt": job.completed_at,  # type: ignore[attr-defined]
                ":updatedAt": JOB_UPDATED_AT,
                ":newVersion": expected_version + 1,
                ":expectedVersion": expected_version,
            }
        ),
        "ReturnValues": "ALL_NEW",
    }
