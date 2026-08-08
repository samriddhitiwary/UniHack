"""DynamoDB PDF table-result repository tests."""

from dataclasses import replace
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.core.exceptions import (
    PdfTableExtractionRepositoryError,
    PdfTableExtractionResultAlreadyExistsError,
    PdfTableExtractionSerializationError,
)
from app.repositories.dynamodb_pdf_table_extraction import (
    DynamoDBPdfTableExtractionRepository,
)
from app.utils.dynamodb import (
    pdf_table_extraction_metadata_to_item,
    pdf_table_extraction_table_to_item,
    serialize_item,
)
from tests.fixtures.pdf_table_extraction import make_pdf_table_extraction_result
from tests.fixtures.processing_jobs import JOB_ID


def conditional_error() -> ClientError:
    return ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")


def test_create_writes_metadata_then_ordered_table_records_conditionally() -> None:
    client = MagicMock()
    result = make_pdf_table_extraction_result()
    repository = DynamoDBPdfTableExtractionRepository(client, "table-results")
    assert repository.create(result) == result
    assert client.put_item.call_count == 3
    calls = client.put_item.call_args_list
    assert calls[0].kwargs["Item"]["recordKey"] == {"S": "META"}
    assert calls[1].kwargs["Item"]["recordKey"] == {"S": "TABLE#000001#000001"}
    assert all("ConditionExpression" in call.kwargs for call in calls)


def test_duplicate_and_client_failures_are_controlled() -> None:
    result = make_pdf_table_extraction_result()
    client = MagicMock()
    client.put_item.side_effect = conditional_error()
    with pytest.raises(PdfTableExtractionResultAlreadyExistsError):
        DynamoDBPdfTableExtractionRepository(client, "table-results").create(result)
    client.put_item.side_effect = ClientError({"Error": {"Code": "Internal"}}, "PutItem")
    with pytest.raises(PdfTableExtractionRepositoryError):
        DynamoDBPdfTableExtractionRepository(client, "table-results").create(result)


def test_get_by_id_reconstructs_paginated_order_without_scan() -> None:
    result = make_pdf_table_extraction_result()
    records = [pdf_table_extraction_metadata_to_item(result)] + [
        pdf_table_extraction_table_to_item(result.extraction_id, table) for table in result.tables
    ]
    client = MagicMock()
    client.query.side_effect = [
        {"Items": [serialize_item(records[2])], "LastEvaluatedKey": {"k": {"S": "next"}}},
        {"Items": [serialize_item(records[0]), serialize_item(records[1])]},
    ]
    restored = DynamoDBPdfTableExtractionRepository(client, "table-results").get_by_id(
        result.extraction_id
    )
    assert restored == result and client.query.call_count == 2
    assert not client.scan.called


def test_get_by_job_id_uses_sparse_index_then_reconstructs() -> None:
    result = make_pdf_table_extraction_result()
    metadata = serialize_item(pdf_table_extraction_metadata_to_item(result))
    client = MagicMock()
    client.query.side_effect = [
        {"Items": [metadata]},
        {
            "Items": [metadata]
            + [
                serialize_item(pdf_table_extraction_table_to_item(result.extraction_id, table))
                for table in result.tables
            ]
        },
    ]
    assert (
        DynamoDBPdfTableExtractionRepository(client, "table-results").get_by_job_id(JOB_ID)
        == result
    )
    assert client.query.call_args_list[0].kwargs["IndexName"] == "JobIdIndex"


def test_missing_and_incomplete_results_are_detected() -> None:
    client = MagicMock()
    client.query.return_value = {"Items": []}
    repository = DynamoDBPdfTableExtractionRepository(client, "table-results")
    assert repository.get_by_id(make_pdf_table_extraction_result().extraction_id) is None
    result = make_pdf_table_extraction_result()
    client.query.return_value = {
        "Items": [serialize_item(pdf_table_extraction_metadata_to_item(result))]
    }
    with pytest.raises(PdfTableExtractionSerializationError):
        repository.get_by_id(result.extraction_id)


def test_oversized_table_is_rejected_before_any_write() -> None:
    result = make_pdf_table_extraction_result()
    huge = result.tables[0]
    huge_cell = replace(huge.rows[0].cells[0], text="x" * 390_000)
    huge_row = replace(huge.rows[0], cells=(huge_cell, huge.rows[0].cells[1]))
    huge = replace(huge, rows=(huge_row, huge.rows[1]))
    oversized = replace(result, tables=(huge, result.tables[1]))
    client = MagicMock()
    with pytest.raises(PdfTableExtractionSerializationError):
        DynamoDBPdfTableExtractionRepository(client, "table-results").create(oversized)
    client.put_item.assert_not_called()
