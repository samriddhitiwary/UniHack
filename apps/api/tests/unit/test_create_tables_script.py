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
    results = MagicMock()
    table_results = MagicMock()
    csv_results = MagicMock()
    image_results = MagicMock()
    ocr_results = MagicMock()
    classification_results = MagicMock()
    category_schemas = MagicMock()
    attribute_results = MagicMock()
    normalization_results = MagicMock()
    conflict_results = MagicMock()
    completeness_results = MagicMock()
    validation_results = MagicMock()
    selection_results = MagicMock()
    review_results = MagicMock()
    reviewed_attribute_results = MagicMock()
    monkeypatch.setattr(create_tables, "create_products_table", products)
    monkeypatch.setattr(create_tables, "create_sources_table", sources)
    monkeypatch.setattr(create_tables, "create_processing_jobs_table", jobs)
    monkeypatch.setattr(create_tables, "create_extraction_results_table", results)
    monkeypatch.setattr(create_tables, "create_table_extraction_results_table", table_results)
    monkeypatch.setattr(create_tables, "create_csv_processing_results_table", csv_results)
    monkeypatch.setattr(create_tables, "create_image_analysis_results_table", image_results)
    monkeypatch.setattr(create_tables, "create_image_ocr_results_table", ocr_results)
    monkeypatch.setattr(
        create_tables,
        "create_product_classification_results_table",
        classification_results,
    )
    monkeypatch.setattr(create_tables, "create_category_attribute_schemas_table", category_schemas)
    monkeypatch.setattr(
        create_tables,
        "create_structured_attribute_extraction_results_table",
        attribute_results,
    )
    monkeypatch.setattr(
        create_tables,
        "create_attribute_normalization_results_table",
        normalization_results,
    )
    monkeypatch.setattr(
        create_tables,
        "create_attribute_conflict_detection_results_table",
        conflict_results,
    )
    monkeypatch.setattr(
        create_tables,
        "create_attribute_completeness_results_table",
        completeness_results,
    )
    monkeypatch.setattr(
        create_tables,
        "create_attribute_validation_results_table",
        validation_results,
    )
    monkeypatch.setattr(
        create_tables,
        "create_attribute_selection_results_table",
        selection_results,
    )
    monkeypatch.setattr(create_tables, "create_product_reviews_table", review_results)
    monkeypatch.setattr(
        create_tables, "create_reviewed_attribute_results_table", reviewed_attribute_results
    )
    assert create_tables.main() == 0
    products.assert_called_once_with()
    sources.assert_called_once_with()
    jobs.assert_called_once_with()
    results.assert_called_once_with()
    table_results.assert_called_once_with()
    csv_results.assert_called_once_with()
    image_results.assert_called_once_with()
    ocr_results.assert_called_once_with()
    classification_results.assert_called_once_with()
    category_schemas.assert_called_once_with()
    attribute_results.assert_called_once_with()
    normalization_results.assert_called_once_with()
    conflict_results.assert_called_once_with()
    completeness_results.assert_called_once_with()
    validation_results.assert_called_once_with()
    selection_results.assert_called_once_with()
    review_results.assert_called_once_with()
    reviewed_attribute_results.assert_called_once_with()


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


def test_extraction_results_table_definition_and_idempotence(monkeypatch: MonkeyPatch) -> None:
    settings = MagicMock(dynamodb_endpoint_url="http://localhost:8001")
    settings.table_name.return_value = "catalogiq-test-extraction-results"
    client = MagicMock()
    client.create_table.side_effect = [{}, _resource_in_use()]
    monkeypatch.setattr(create_tables, "get_settings", lambda: settings)
    monkeypatch.setattr(create_tables, "create_dynamodb_client", lambda _: client)

    assert create_tables.create_extraction_results_table() is True
    assert create_tables.create_extraction_results_table() is False
    request = client.create_table.call_args_list[0].kwargs
    assert request["KeySchema"] == [
        {"AttributeName": "extractionId", "KeyType": "HASH"},
        {"AttributeName": "recordKey", "KeyType": "RANGE"},
    ]
    assert request["GlobalSecondaryIndexes"] == [
        {
            "IndexName": "JobIdIndex",
            "KeySchema": [
                {"AttributeName": "jobId", "KeyType": "HASH"},
                {"AttributeName": "createdAt", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "ALL"},
        }
    ]
    assert client.get_waiter.return_value.wait.call_count == 2


def test_table_extraction_results_table_definition_and_idempotence(
    monkeypatch: MonkeyPatch,
) -> None:
    settings = MagicMock(dynamodb_endpoint_url="http://localhost:8001")
    settings.table_name.return_value = "catalogiq-test-table-extraction-results"
    client = MagicMock()
    client.create_table.side_effect = [{}, _resource_in_use()]
    monkeypatch.setattr(create_tables, "get_settings", lambda: settings)
    monkeypatch.setattr(create_tables, "create_dynamodb_client", lambda _: client)

    assert create_tables.create_table_extraction_results_table() is True
    assert create_tables.create_table_extraction_results_table() is False
    request = client.create_table.call_args_list[0].kwargs
    assert request["KeySchema"] == [
        {"AttributeName": "extractionId", "KeyType": "HASH"},
        {"AttributeName": "recordKey", "KeyType": "RANGE"},
    ]
    assert request["GlobalSecondaryIndexes"][0]["IndexName"] == "JobIdIndex"


def test_csv_processing_results_table_definition_and_idempotence(
    monkeypatch: MonkeyPatch,
) -> None:
    settings = MagicMock(dynamodb_endpoint_url="http://localhost:8001")
    settings.table_name.return_value = "catalogiq-test-csv-processing-results"
    client = MagicMock()
    client.create_table.side_effect = [{}, _resource_in_use()]
    monkeypatch.setattr(create_tables, "get_settings", lambda: settings)
    monkeypatch.setattr(create_tables, "create_dynamodb_client", lambda _: client)
    assert create_tables.create_csv_processing_results_table() is True
    assert create_tables.create_csv_processing_results_table() is False
    request = client.create_table.call_args_list[0].kwargs
    assert request["KeySchema"] == [
        {"AttributeName": "processingId", "KeyType": "HASH"},
        {"AttributeName": "recordKey", "KeyType": "RANGE"},
    ]
    assert request["GlobalSecondaryIndexes"][0]["IndexName"] == "JobIdIndex"


def test_image_analysis_results_table_definition_and_idempotence(
    monkeypatch: MonkeyPatch,
) -> None:
    settings = MagicMock(dynamodb_endpoint_url="http://localhost:8001")
    settings.table_name.return_value = "catalogiq-test-image-analysis-results"
    client = MagicMock()
    client.create_table.side_effect = [{}, _resource_in_use()]
    monkeypatch.setattr(create_tables, "get_settings", lambda: settings)
    monkeypatch.setattr(create_tables, "create_dynamodb_client", lambda _: client)
    assert create_tables.create_image_analysis_results_table() is True
    assert create_tables.create_image_analysis_results_table() is False
    request = client.create_table.call_args_list[0].kwargs
    assert request["KeySchema"] == [
        {"AttributeName": "analysisId", "KeyType": "HASH"},
        {"AttributeName": "recordKey", "KeyType": "RANGE"},
    ]
    assert request["GlobalSecondaryIndexes"][0]["IndexName"] == "JobIdIndex"


def test_image_ocr_results_table_definition_and_idempotence(
    monkeypatch: MonkeyPatch,
) -> None:
    settings = MagicMock(dynamodb_endpoint_url="http://localhost:8001")
    settings.table_name.return_value = "catalogiq-test-image-ocr-results"
    client = MagicMock()
    client.create_table.side_effect = [{}, _resource_in_use()]
    monkeypatch.setattr(create_tables, "get_settings", lambda: settings)
    monkeypatch.setattr(create_tables, "create_dynamodb_client", lambda _: client)
    assert create_tables.create_image_ocr_results_table() is True
    assert create_tables.create_image_ocr_results_table() is False
    request = client.create_table.call_args_list[0].kwargs
    assert request["TableName"] == "catalogiq-test-image-ocr-results"
    assert request["KeySchema"] == [
        {"AttributeName": "ocrId", "KeyType": "HASH"},
        {"AttributeName": "recordKey", "KeyType": "RANGE"},
    ]
    assert request["GlobalSecondaryIndexes"] == [
        {
            "IndexName": "JobIdIndex",
            "KeySchema": [
                {"AttributeName": "jobId", "KeyType": "HASH"},
                {"AttributeName": "createdAt", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "ALL"},
        }
    ]


def test_product_classification_results_table_definition(monkeypatch: MonkeyPatch) -> None:
    settings = MagicMock(dynamodb_endpoint_url="http://localhost:8001")
    settings.table_name.return_value = "catalogiq-test-product-classification-results"
    client = MagicMock()
    monkeypatch.setattr(create_tables, "get_settings", lambda: settings)
    monkeypatch.setattr(create_tables, "create_dynamodb_client", lambda _: client)
    assert create_tables.create_product_classification_results_table() is True
    request = client.create_table.call_args.kwargs
    assert request["KeySchema"] == [
        {"AttributeName": "classificationId", "KeyType": "HASH"},
        {"AttributeName": "recordKey", "KeyType": "RANGE"},
    ]
    assert request["GlobalSecondaryIndexes"][0]["IndexName"] == "JobIdIndex"


def test_category_attribute_schemas_table_definition_and_idempotence(
    monkeypatch: MonkeyPatch,
) -> None:
    settings = MagicMock(dynamodb_endpoint_url="http://localhost:8001")
    settings.table_name.return_value = "catalogiq-test-category-attribute-schemas"
    client = MagicMock()
    client.create_table.side_effect = [{}, _resource_in_use()]
    monkeypatch.setattr(create_tables, "get_settings", lambda: settings)
    monkeypatch.setattr(create_tables, "create_dynamodb_client", lambda _: client)
    assert create_tables.create_category_attribute_schemas_table() is True
    assert create_tables.create_category_attribute_schemas_table() is False
    request = client.create_table.call_args_list[0].kwargs
    assert request["AttributeDefinitions"] == [
        {"AttributeName": "category", "AttributeType": "S"},
        {"AttributeName": "version", "AttributeType": "N"},
    ]
    assert request["KeySchema"] == [
        {"AttributeName": "category", "KeyType": "HASH"},
        {"AttributeName": "version", "KeyType": "RANGE"},
    ]
    assert "GlobalSecondaryIndexes" not in request


def test_structured_attribute_extraction_results_table_definition(
    monkeypatch: MonkeyPatch,
) -> None:
    settings = MagicMock(dynamodb_endpoint_url="http://localhost:8001")
    settings.table_name.return_value = "catalogiq-test-structured-attribute-extraction-results"
    client = MagicMock()
    monkeypatch.setattr(create_tables, "get_settings", lambda: settings)
    monkeypatch.setattr(create_tables, "create_dynamodb_client", lambda _: client)
    assert create_tables.create_structured_attribute_extraction_results_table() is True
    request = client.create_table.call_args.kwargs
    assert request["KeySchema"] == [
        {"AttributeName": "extractionId", "KeyType": "HASH"},
        {"AttributeName": "recordKey", "KeyType": "RANGE"},
    ]
    assert request["GlobalSecondaryIndexes"][0]["IndexName"] == "JobIdIndex"


def test_attribute_normalization_results_table_definition(monkeypatch: MonkeyPatch) -> None:
    settings = MagicMock(dynamodb_endpoint_url="http://localhost:8001")
    settings.table_name.return_value = "catalogiq-test-attribute-normalization-results"
    client = MagicMock()
    monkeypatch.setattr(create_tables, "get_settings", lambda: settings)
    monkeypatch.setattr(create_tables, "create_dynamodb_client", lambda _: client)
    assert create_tables.create_attribute_normalization_results_table() is True
    request = client.create_table.call_args.kwargs
    assert request["KeySchema"] == [
        {"AttributeName": "normalizationId", "KeyType": "HASH"},
        {"AttributeName": "recordKey", "KeyType": "RANGE"},
    ]
    assert request["GlobalSecondaryIndexes"][0]["IndexName"] == "JobIdIndex"


def test_attribute_conflict_detection_results_table_definition(
    monkeypatch: MonkeyPatch,
) -> None:
    settings = MagicMock(dynamodb_endpoint_url="http://localhost:8001")
    settings.table_name.return_value = "catalogiq-test-attribute-conflict-detection-results"
    client = MagicMock()
    monkeypatch.setattr(create_tables, "get_settings", lambda: settings)
    monkeypatch.setattr(create_tables, "create_dynamodb_client", lambda _: client)
    assert create_tables.create_attribute_conflict_detection_results_table() is True
    request = client.create_table.call_args.kwargs
    assert request["KeySchema"] == [
        {"AttributeName": "conflictDetectionId", "KeyType": "HASH"},
        {"AttributeName": "recordKey", "KeyType": "RANGE"},
    ]
    assert request["GlobalSecondaryIndexes"][0]["IndexName"] == "JobIdIndex"


def test_attribute_completeness_results_table_definition(monkeypatch: MonkeyPatch) -> None:
    settings = MagicMock(dynamodb_endpoint_url="http://localhost:8001")
    settings.table_name.return_value = "catalogiq-test-attribute-completeness-results"
    client = MagicMock()
    monkeypatch.setattr(create_tables, "get_settings", lambda: settings)
    monkeypatch.setattr(create_tables, "create_dynamodb_client", lambda _: client)
    assert create_tables.create_attribute_completeness_results_table() is True
    request = client.create_table.call_args.kwargs
    assert request["KeySchema"] == [
        {"AttributeName": "completenessId", "KeyType": "HASH"},
        {"AttributeName": "recordKey", "KeyType": "RANGE"},
    ]
    assert request["GlobalSecondaryIndexes"][0]["IndexName"] == "JobIdIndex"


def test_attribute_validation_results_table_definition(monkeypatch: MonkeyPatch) -> None:
    settings = MagicMock(dynamodb_endpoint_url="http://localhost:8001")
    settings.table_name.return_value = "catalogiq-test-attribute-validation-results"
    client = MagicMock()
    monkeypatch.setattr(create_tables, "get_settings", lambda: settings)
    monkeypatch.setattr(create_tables, "create_dynamodb_client", lambda _: client)
    assert create_tables.create_attribute_validation_results_table() is True
    request = client.create_table.call_args.kwargs
    assert request["KeySchema"] == [
        {"AttributeName": "validationId", "KeyType": "HASH"},
        {"AttributeName": "recordKey", "KeyType": "RANGE"},
    ]
    assert request["GlobalSecondaryIndexes"][0]["IndexName"] == "JobIdIndex"


def test_attribute_selection_results_table_definition(monkeypatch: MonkeyPatch) -> None:
    settings = MagicMock(dynamodb_endpoint_url="http://localhost:8001")
    settings.table_name.return_value = "catalogiq-test-attribute-selection-results"
    client = MagicMock()
    monkeypatch.setattr(create_tables, "get_settings", lambda: settings)
    monkeypatch.setattr(create_tables, "create_dynamodb_client", lambda _: client)
    assert create_tables.create_attribute_selection_results_table() is True
    request = client.create_table.call_args.kwargs
    assert request["KeySchema"] == [
        {"AttributeName": "selectionId", "KeyType": "HASH"},
        {"AttributeName": "recordKey", "KeyType": "RANGE"},
    ]
    assert request["GlobalSecondaryIndexes"][0]["IndexName"] == "JobIdIndex"


def test_product_reviews_table_definition_and_idempotence(monkeypatch: MonkeyPatch) -> None:
    settings = MagicMock(dynamodb_endpoint_url="http://localhost:8001")
    settings.table_name.return_value = "catalogiq-test-product-reviews"
    client = MagicMock()
    client.create_table.side_effect = [{}, _resource_in_use()]
    monkeypatch.setattr(create_tables, "get_settings", lambda: settings)
    monkeypatch.setattr(create_tables, "create_dynamodb_client", lambda _: client)
    assert create_tables.create_product_reviews_table() is True
    assert create_tables.create_product_reviews_table() is False
    request = client.create_table.call_args_list[0].kwargs
    assert request["KeySchema"] == [
        {"AttributeName": "reviewId", "KeyType": "HASH"},
        {"AttributeName": "recordKey", "KeyType": "RANGE"},
    ]
    assert "GlobalSecondaryIndexes" not in request


def test_reviewed_attribute_results_table_definition(monkeypatch: MonkeyPatch) -> None:
    settings = MagicMock(dynamodb_endpoint_url="http://localhost:8001")
    settings.table_name.return_value = "catalogiq-test-reviewed-attribute-results"
    client = MagicMock()
    monkeypatch.setattr(create_tables, "get_settings", lambda: settings)
    monkeypatch.setattr(create_tables, "create_dynamodb_client", lambda _: client)
    assert create_tables.create_reviewed_attribute_results_table() is True
    request = client.create_table.call_args.kwargs
    assert request["KeySchema"] == [
        {"AttributeName": "materializationId", "KeyType": "HASH"},
        {"AttributeName": "recordKey", "KeyType": "RANGE"},
    ]
    assert [item["IndexName"] for item in request["GlobalSecondaryIndexes"]] == [
        "JobIdIndex",
        "ReviewIdIndex",
    ]
