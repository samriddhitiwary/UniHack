"""Idempotent local DynamoDB table-definition tests."""

import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

from _pytest.monkeypatch import MonkeyPatch
from botocore.exceptions import ClientError


def _load_create_tables() -> ModuleType:
    path = Path(__file__).parents[4] / "scripts" / "dynamodb" / "create_tables.py"
    spec = importlib.util.spec_from_file_location("catalogiq_create_tables", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load create_tables.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


create_tables = _load_create_tables()


def _resource_in_use() -> ClientError:
    return ClientError(
        {"Error": {"Code": "ResourceInUseException", "Message": "exists"}},
        "CreateTable",
    )


def test_sources_table_definition_and_idempotence(monkeypatch: MonkeyPatch) -> None:
    settings = MagicMock(dynamodb_endpoint_url="http://localhost:8001")
    settings.table_name.return_value = "catalogiq-test-sources"
    client = MagicMock()
    client.create_table.side_effect = [{}, _resource_in_use()]
    monkeypatch.setattr(create_tables, "get_settings", lambda: settings)
    monkeypatch.setattr(create_tables, "create_dynamodb_client", lambda _: client)

    assert create_tables.create_sources_table() is True
    assert create_tables.create_sources_table() is False

    request = client.create_table.call_args_list[0].kwargs
    assert request["TableName"] == "catalogiq-test-sources"
    assert request["KeySchema"] == [
        {"AttributeName": "productId", "KeyType": "HASH"},
        {"AttributeName": "sourceId", "KeyType": "RANGE"},
    ]
    assert request["GlobalSecondaryIndexes"] == [
        {
            "IndexName": "ProductCreatedAtIndex",
            "KeySchema": [
                {"AttributeName": "productId", "KeyType": "HASH"},
                {"AttributeName": "createdAt", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "ALL"},
        }
    ]
    assert client.get_waiter.return_value.wait.call_count == 2


def test_main_keeps_products_table_creation(monkeypatch: MonkeyPatch) -> None:
    products = MagicMock()
    sources = MagicMock()
    jobs = MagicMock()
    monkeypatch.setattr(create_tables, "create_products_table", products)
    monkeypatch.setattr(create_tables, "create_sources_table", sources)
    monkeypatch.setattr(create_tables, "create_processing_jobs_table", jobs)
    assert create_tables.main() == 0
    products.assert_called_once_with()
    sources.assert_called_once_with()
    jobs.assert_called_once_with()


def test_processing_jobs_table_definition_and_idempotence(monkeypatch: MonkeyPatch) -> None:
    settings = MagicMock(dynamodb_endpoint_url="http://localhost:8001")
    settings.table_name.return_value = "catalogiq-test-processing-jobs"
    client = MagicMock()
    client.create_table.side_effect = [{}, _resource_in_use()]
    monkeypatch.setattr(create_tables, "get_settings", lambda: settings)
    monkeypatch.setattr(create_tables, "create_dynamodb_client", lambda _: client)

    assert create_tables.create_processing_jobs_table() is True
    assert create_tables.create_processing_jobs_table() is False

    request = client.create_table.call_args_list[0].kwargs
    assert request["TableName"] == "catalogiq-test-processing-jobs"
    assert request["KeySchema"] == [{"AttributeName": "jobId", "KeyType": "HASH"}]
    assert request["GlobalSecondaryIndexes"] == [
        {
            "IndexName": "ProductCreatedAtIndex",
            "KeySchema": [
                {"AttributeName": "productId", "KeyType": "HASH"},
                {"AttributeName": "createdAt", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "ALL"},
        },
        {
            "IndexName": "SourceCreatedAtIndex",
            "KeySchema": [
                {"AttributeName": "sourceScope", "KeyType": "HASH"},
                {"AttributeName": "createdAt", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "ALL"},
        },
    ]
    assert client.get_waiter.return_value.wait.call_count == 2
