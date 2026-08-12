"""DynamoDB image-analysis result repository tests."""

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.core.exceptions import (
    ImageAnalysisRepositoryError,
    ImageAnalysisResultAlreadyExistsError,
    ImageAnalysisSerializationError,
)
from app.repositories import dynamodb_image_analysis as repository_module
from app.repositories.dynamodb_image_analysis import DynamoDBImageAnalysisResultRepository
from app.utils.dynamodb import (
    image_analysis_metadata_to_item,
    image_analysis_region_to_item,
    serialize_item,
)
from tests.fixtures.image_analysis import make_image_analysis_result
from tests.fixtures.processing_jobs import JOB_ID


def conditional_error() -> ClientError:
    return ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")


def raw_records():
    result = make_image_analysis_result()
    records = [image_analysis_metadata_to_item(result)] + [
        image_analysis_region_to_item(result.analysis_id, index, region)
        for index, region in enumerate(result.regions, start=1)
    ]
    return result, records


def test_create_writes_meta_then_regions_conditionally() -> None:
    client = MagicMock()
    result, _ = raw_records()
    assert DynamoDBImageAnalysisResultRepository(client, "images").create(result) == result
    assert client.put_item.call_count == 7
    assert client.put_item.call_args_list[0].kwargs["Item"]["recordKey"] == {"S": "META"}
    assert client.put_item.call_args_list[-1].kwargs["Item"]["recordKey"] == {"S": "REGION#000006"}


def test_duplicate_and_client_failures_are_controlled() -> None:
    result, _ = raw_records()
    client = MagicMock()
    client.put_item.side_effect = conditional_error()
    with pytest.raises(ImageAnalysisResultAlreadyExistsError):
        DynamoDBImageAnalysisResultRepository(client, "images").create(result)
    client.put_item.side_effect = ClientError({"Error": {"Code": "Internal"}}, "PutItem")
    with pytest.raises(ImageAnalysisRepositoryError):
        DynamoDBImageAnalysisResultRepository(client, "images").create(result)


def test_get_by_id_paginates_orders_and_never_scans() -> None:
    result, raw = raw_records()
    client = MagicMock()
    client.query.side_effect = [
        {"Items": [serialize_item(raw[-1])], "LastEvaluatedKey": {"k": {"S": "next"}}},
        {"Items": [serialize_item(item) for item in raw[:-1]]},
    ]
    assert (
        DynamoDBImageAnalysisResultRepository(client, "images").get_by_id(result.analysis_id)
        == result
    )
    assert client.query.call_count == 2 and not client.scan.called


def test_get_by_job_id_uses_sparse_index_then_partition() -> None:
    result, raw = raw_records()
    client = MagicMock()
    client.query.side_effect = [
        {"Items": [serialize_item(raw[0])]},
        {"Items": [serialize_item(item) for item in raw]},
    ]
    assert DynamoDBImageAnalysisResultRepository(client, "images").get_by_job_id(JOB_ID) == result
    assert client.query.call_args_list[0].kwargs["IndexName"] == "JobIdIndex"


def test_missing_and_incomplete_results_are_detected() -> None:
    result, raw = raw_records()
    client = MagicMock()
    client.query.return_value = {"Items": []}
    repository = DynamoDBImageAnalysisResultRepository(client, "images")
    assert repository.get_by_id(result.analysis_id) is None
    client.query.return_value = {"Items": [serialize_item(item) for item in raw[:-1]]}
    with pytest.raises(ImageAnalysisSerializationError):
        repository.get_by_id(result.analysis_id)


def test_oversized_record_is_rejected_before_any_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, _ = raw_records()
    client = MagicMock()
    monkeypatch.setattr(
        repository_module,
        "_wire_size",
        lambda _item: repository_module.MAX_SAFE_ITEM_BYTES + 1,
    )
    with pytest.raises(ImageAnalysisSerializationError):
        DynamoDBImageAnalysisResultRepository(client, "images").create(result)
    client.put_item.assert_not_called()
