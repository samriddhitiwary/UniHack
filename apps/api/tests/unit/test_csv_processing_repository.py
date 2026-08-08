"""DynamoDB CSV processing-result repository tests."""

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.core.exceptions import (
    CsvProcessingRepositoryError,
    CsvProcessingResultAlreadyExistsError,
    CsvProcessingSerializationError,
    CsvResultItemTooLargeError,
)
from app.domain.csv_processing import CsvRow
from app.repositories.dynamodb_csv_processing import DynamoDBCsvProcessingResultRepository
from app.utils.dynamodb import (
    csv_processing_metadata_to_item,
    csv_processing_row_to_item,
    serialize_item,
)
from tests.fixtures.csv_processing import make_csv_processing_result
from tests.fixtures.processing_jobs import JOB_ID


def conditional_error() -> ClientError:
    return ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")


def test_create_writes_meta_then_ordered_rows_conditionally() -> None:
    client = MagicMock()
    result = make_csv_processing_result()
    repository = DynamoDBCsvProcessingResultRepository(client, "csv-results")
    assert repository.create(result) == result
    assert client.put_item.call_count == 3
    calls = client.put_item.call_args_list
    assert calls[0].kwargs["Item"]["recordKey"] == {"S": "META"}
    assert calls[1].kwargs["Item"]["recordKey"] == {"S": "ROW#000000001"}
    assert all("ConditionExpression" in call.kwargs for call in calls)


def test_duplicate_and_client_failures_are_controlled() -> None:
    result = make_csv_processing_result()
    client = MagicMock()
    client.put_item.side_effect = conditional_error()
    with pytest.raises(CsvProcessingResultAlreadyExistsError):
        DynamoDBCsvProcessingResultRepository(client, "csv-results").create(result)
    client.put_item.side_effect = ClientError({"Error": {"Code": "Internal"}}, "PutItem")
    with pytest.raises(CsvProcessingRepositoryError):
        DynamoDBCsvProcessingResultRepository(client, "csv-results").create(result)


def test_get_by_id_reconstructs_paginated_rows_without_scan() -> None:
    result = make_csv_processing_result()
    raw = [csv_processing_metadata_to_item(result)] + [
        csv_processing_row_to_item(result.processing_id, row) for row in result.rows
    ]
    client = MagicMock()
    client.query.side_effect = [
        {"Items": [serialize_item(raw[2])], "LastEvaluatedKey": {"k": {"S": "next"}}},
        {"Items": [serialize_item(raw[0]), serialize_item(raw[1])]},
    ]
    restored = DynamoDBCsvProcessingResultRepository(client, "csv-results").get_by_id(
        result.processing_id
    )
    assert restored == result and client.query.call_count == 2 and not client.scan.called


def test_get_by_job_id_uses_sparse_index_then_partition_query() -> None:
    result = make_csv_processing_result()
    metadata = serialize_item(csv_processing_metadata_to_item(result))
    rows = [
        serialize_item(csv_processing_row_to_item(result.processing_id, row)) for row in result.rows
    ]
    client = MagicMock()
    client.query.side_effect = [{"Items": [metadata]}, {"Items": [metadata, *rows]}]
    assert (
        DynamoDBCsvProcessingResultRepository(client, "csv-results").get_by_job_id(JOB_ID) == result
    )
    assert client.query.call_args_list[0].kwargs["IndexName"] == "JobIdIndex"


def test_missing_and_incomplete_partitions_are_detected() -> None:
    client = MagicMock()
    client.query.return_value = {"Items": []}
    repository = DynamoDBCsvProcessingResultRepository(client, "csv-results")
    result = make_csv_processing_result()
    assert repository.get_by_id(result.processing_id) is None
    client.query.return_value = {"Items": [serialize_item(csv_processing_metadata_to_item(result))]}
    with pytest.raises(CsvProcessingSerializationError):
        repository.get_by_id(result.processing_id)


def test_header_only_result_is_one_meta_item() -> None:
    client = MagicMock()
    result = make_csv_processing_result(rows=())
    assert DynamoDBCsvProcessingResultRepository(client, "csv-results").create(result) == result
    client.put_item.assert_called_once()


def test_oversized_row_is_rejected_before_any_write() -> None:
    huge = CsvRow.create(1, ["x" * 390_000, "B", "C"], 3)
    result = make_csv_processing_result(rows=(huge,))
    client = MagicMock()
    with pytest.raises(CsvResultItemTooLargeError):
        DynamoDBCsvProcessingResultRepository(client, "csv-results").create(result)
    client.put_item.assert_not_called()
