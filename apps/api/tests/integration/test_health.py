"""Health route integration tests."""

from unittest.mock import Mock

from botocore.exceptions import EndpointConnectionError
from fastapi.testclient import TestClient

from app.api.dependencies.dynamodb import get_dynamodb_health
from app.main import app


def test_liveness_response(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "catalogiq-api",
        "version": "0.1.0",
    }


def test_readiness_when_dynamodb_is_available(client: TestClient) -> None:
    dependency = Mock()
    app.dependency_overrides[get_dynamodb_health] = lambda: dependency
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": {"dynamodb": "available"},
    }
    dependency.check.assert_called_once_with()


def test_readiness_hides_dependency_failure_details(client: TestClient) -> None:
    dependency = Mock()
    dependency.check.side_effect = EndpointConnectionError(endpoint_url="http://secret-host")
    app.dependency_overrides[get_dynamodb_health] = lambda: dependency
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body == {
        "detail": {
            "status": "not_ready",
            "dependencies": {"dynamodb": "unavailable"},
        }
    }
    assert "secret-host" not in response.text
