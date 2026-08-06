"""DynamoDB client configuration tests."""

from unittest.mock import MagicMock, patch

from app.api.dependencies.dynamodb import DynamoDBHealth, create_dynamodb_client
from app.core.config import Settings


def test_health_check_uses_bounded_list_tables_request() -> None:
    client = MagicMock()
    DynamoDBHealth(client).check()
    client.list_tables.assert_called_once_with(Limit=1)


@patch("app.api.dependencies.dynamodb.boto3.client")
def test_local_client_uses_endpoint_and_dummy_credentials(client_factory: MagicMock) -> None:
    settings = Settings(dynamodb_endpoint_url="http://localhost:8001")
    create_dynamodb_client(settings)
    kwargs = client_factory.call_args.kwargs
    assert kwargs["endpoint_url"] == "http://localhost:8001"
    assert kwargs["aws_access_key_id"] == "local"
    assert kwargs["aws_secret_access_key"] == "local"


@patch("app.api.dependencies.dynamodb.boto3.client")
def test_aws_client_omits_endpoint_and_explicit_credentials(client_factory: MagicMock) -> None:
    settings = Settings(dynamodb_endpoint_url="")
    create_dynamodb_client(settings)
    kwargs = client_factory.call_args.kwargs
    assert "endpoint_url" not in kwargs
    assert "aws_access_key_id" not in kwargs
    assert "aws_secret_access_key" not in kwargs
