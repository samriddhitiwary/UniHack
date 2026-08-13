"""DynamoDB image OCR result repository tests."""

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.core.exceptions import (
    ImageOcrRepositoryError,
    ImageOcrResultAlreadyExistsError,
    ImageOcrResultItemTooLargeError,
    ImageOcrSerializationError,
)
from app.repositories import dynamodb_image_ocr as repository_module
from app.repositories.dynamodb_image_ocr import DynamoDBImageOcrResultRepository
from app.utils.dynamodb import (
    image_ocr_block_to_item,
    image_ocr_metadata_to_item,
    serialize_item,
)
from tests.fixtures.image_ocr import make_image_ocr_result
from tests.fixtures.processing_jobs import SECOND_JOB_ID


def conditional_error() -> ClientError:
    return ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")


def raw_records():
    result = make_image_ocr_result()
    records = [image_ocr_metadata_to_item(result)] + [
        image_ocr_block_to_item(result.ocr_id, index, block)
        for index, block in enumerate(result.blocks, start=1)
    ]
    return result, records


def test_create_writes_meta_then_blocks_conditionally() -> None:
    client = MagicMock()
    result, _ = raw_records()
    assert DynamoDBImageOcrResultRepository(client, "ocr").create(result) == result
    assert client.put_item.call_count == 2
    assert client.put_item.call_args_list[0].kwargs["Item"]["recordKey"] == {"S": "META"}
    assert client.put_item.call_args_list[1].kwargs["Item"]["recordKey"] == {"S": "BLOCK#000001"}


def test_duplicate_and_client_failures_are_controlled() -> None:
    result, _ = raw_records()
    client = MagicMock()
    client.put_item.side_effect = conditional_error()
    with pytest.raises(ImageOcrResultAlreadyExistsError):
        DynamoDBImageOcrResultRepository(client, "ocr").create(result)
    client.put_item.side_effect = ClientError({"Error": {"Code": "Internal"}}, "PutItem")
    with pytest.raises(ImageOcrRepositoryError):
        DynamoDBImageOcrResultRepository(client, "ocr").create(result)


def test_get_by_id_paginates_orders_and_never_scans() -> None:
    result, raw = raw_records()
    client = MagicMock()
    client.query.side_effect = [
        {"Items": [serialize_item(raw[-1])], "LastEvaluatedKey": {"k": {"S": "next"}}},
        {"Items": [serialize_item(raw[0])]},
    ]
    assert DynamoDBImageOcrResultRepository(client, "ocr").get_by_id(result.ocr_id) == result
    assert client.query.call_count == 2 and not client.scan.called


def test_get_by_job_id_uses_sparse_index_then_partition() -> None:
    result, raw = raw_records()
    client = MagicMock()
    client.query.side_effect = [
        {"Items": [serialize_item(raw[0])]},
        {"Items": [serialize_item(value) for value in raw]},
    ]
    assert DynamoDBImageOcrResultRepository(client, "ocr").get_by_job_id(SECOND_JOB_ID) == result
    assert client.query.call_args_list[0].kwargs["IndexName"] == "JobIdIndex"


def test_missing_and_incomplete_results_are_detected() -> None:
    _, raw = raw_records()
    client = MagicMock()
    client.query.return_value = {"Items": []}
    repository = DynamoDBImageOcrResultRepository(client, "ocr")
    assert repository.get_by_id(make_image_ocr_result().ocr_id) is None
    client.query.return_value = {"Items": [serialize_item(raw[0])]}
    with pytest.raises(ImageOcrSerializationError):
        repository.get_by_id(make_image_ocr_result().ocr_id)


def test_oversized_record_is_rejected_before_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    result, _ = raw_records()
    client = MagicMock()
    monkeypatch.setattr(
        repository_module,
        "_wire_size",
        lambda _item: repository_module.MAX_SAFE_ITEM_BYTES + 1,
    )
    with pytest.raises(ImageOcrResultItemTooLargeError):
        DynamoDBImageOcrResultRepository(client, "ocr").create(result)
    client.put_item.assert_not_called()
