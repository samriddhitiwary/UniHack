"""Product create/retrieve API and OpenAPI contract tests."""

from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.products import get_product_service
from app.core.exceptions import ProductAlreadyExistsError, ProductRepositoryError
from app.domain.products import Product
from app.main import app
from app.repositories.products import ProductRepository
from app.services.products import ProductService
from tests.fixtures.products import PRODUCT_ID, make_product


class MemoryProductRepository:
    def __init__(self, product: Product | None = None, error: Exception | None = None) -> None:
        self.product = product
        self.error = error

    def create(self, product: Product) -> Product:
        if self.error is not None:
            raise self.error
        self.product = product
        return product

    def get_by_id(self, product_id: UUID) -> Product | None:
        if self.error is not None:
            raise self.error
        if self.product is not None and self.product.product_id == product_id:
            return self.product
        return None


def _override(repository: MemoryProductRepository) -> None:
    service = ProductService(cast(ProductRepository, repository))
    app.dependency_overrides[get_product_service] = lambda: service


def test_create_product_returns_201_and_stable_camel_case_response(client: TestClient) -> None:
    _override(MemoryProductRepository())
    response = client.post(
        "/api/v1/products",
        json={
            "name": "  PX-400 Centrifugal Pump  ",
            "manufacturer": "ABC Industries",
            "modelNumber": "PX-400",
            "category": "CENTRIFUGAL_PUMP",
            "description": "Industrial centrifugal pump",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["productId"])
    assert body["name"] == "PX-400 Centrifugal Pump"
    assert body["modelNumber"] == "PX-400"
    assert body["status"] == "DRAFT"
    assert body["sourceCount"] == 0
    assert body["version"] == 1
    assert body["createdAt"].endswith("Z")
    assert body["updatedAt"] == body["createdAt"]
    assert "entityType" not in body
    assert response.headers["X-Request-ID"]


@pytest.mark.parametrize(
    "payload",
    [
        {"name": ""},
        {"name": "Valid product", "category": "UNKNOWN"},
        {"name": "Valid product", "productId": str(PRODUCT_ID)},
        {"name": "Valid product", "status": "DRAFT"},
        {"name": "Valid product", "unknownField": "value"},
        {"name": "Valid product", "description": "x" * 4_001},
    ],
)
def test_create_rejects_invalid_or_system_managed_fields(
    client: TestClient, payload: dict[str, object]
) -> None:
    _override(MemoryProductRepository())
    response = client.post("/api/v1/products", json=payload)
    assert response.status_code == 422
    _assert_error(response.json(), "REQUEST_VALIDATION_FAILED")


def test_create_normalizes_empty_optional_values(client: TestClient) -> None:
    _override(MemoryProductRepository())
    response = client.post(
        "/api/v1/products",
        json={"name": "Valid product", "manufacturer": " ", "modelNumber": ""},
    )
    assert response.status_code == 201
    assert response.json()["manufacturer"] is None
    assert response.json()["modelNumber"] is None


def test_duplicate_product_returns_safe_409(client: TestClient) -> None:
    _override(MemoryProductRepository(error=ProductAlreadyExistsError(PRODUCT_ID)))
    response = client.post("/api/v1/products", json={"name": "Valid product"})
    assert response.status_code == 409
    body = response.json()
    _assert_error(body, "PRODUCT_ALREADY_EXISTS")
    assert body["error"]["details"] == {"productId": str(PRODUCT_ID)}


def test_create_repository_failure_returns_safe_503(client: TestClient) -> None:
    _override(MemoryProductRepository(error=ProductRepositoryError("secret-table-name")))
    response = client.post("/api/v1/products", json={"name": "Valid product"})
    assert response.status_code == 503
    _assert_error(response.json(), "PRODUCT_STORAGE_UNAVAILABLE")
    assert "secret-table-name" not in response.text


def test_retrieve_existing_product_returns_200(client: TestClient) -> None:
    _override(MemoryProductRepository(product=make_product()))
    response = client.get(f"/api/v1/products/{PRODUCT_ID}")
    assert response.status_code == 200
    assert response.json()["productId"] == str(PRODUCT_ID)
    assert response.json()["category"] == "CENTRIFUGAL_PUMP"
    assert "entityType" not in response.json()


def test_retrieve_missing_product_returns_safe_404(client: TestClient) -> None:
    _override(MemoryProductRepository())
    response = client.get(f"/api/v1/products/{PRODUCT_ID}")
    assert response.status_code == 404
    body = response.json()
    _assert_error(body, "PRODUCT_NOT_FOUND")
    assert body["error"]["details"] == {"productId": str(PRODUCT_ID)}


def test_retrieve_rejects_invalid_uuid(client: TestClient) -> None:
    _override(MemoryProductRepository())
    response = client.get("/api/v1/products/not-a-uuid")
    assert response.status_code == 422
    _assert_error(response.json(), "REQUEST_VALIDATION_FAILED")


def test_retrieve_repository_failure_hides_dynamodb_details(client: TestClient) -> None:
    _override(MemoryProductRepository(error=ProductRepositoryError("aws-request-id")))
    response = client.get(f"/api/v1/products/{PRODUCT_ID}")
    assert response.status_code == 503
    _assert_error(response.json(), "PRODUCT_STORAGE_UNAVAILABLE")
    assert "aws-request-id" not in response.text


def test_unexpected_failure_returns_safe_500() -> None:
    _override(MemoryProductRepository(error=RuntimeError("internal secret")))
    try:
        with TestClient(app, raise_server_exceptions=False) as safe_client:
            response = safe_client.get(f"/api/v1/products/{PRODUCT_ID}")
        assert response.status_code == 500
        _assert_error(response.json(), "INTERNAL_SERVER_ERROR")
        assert "internal secret" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_openapi_documents_only_approved_product_operations(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    collection = schema["paths"]["/api/v1/products"]
    member = schema["paths"]["/api/v1/products/{product_id}"]
    assert set(collection) == {"post"}
    assert set(member) == {"get"}
    assert collection["post"]["responses"]["201"]
    assert collection["post"]["responses"]["409"]
    assert collection["post"]["responses"]["422"]
    assert collection["post"]["responses"]["503"]
    assert member["get"]["responses"]["200"]
    assert member["get"]["responses"]["404"]
    assert member["get"]["responses"]["422"]
    assert member["get"]["responses"]["503"]
    assert member["get"]["parameters"][0]["schema"]["format"] == "uuid"
    category_schema = schema["components"]["schemas"]["ProductCategory"]
    assert category_schema["enum"] == ["UNCLASSIFIED", "CENTRIFUGAL_PUMP", "INDUCTION_MOTOR"]
    record_properties = schema["components"]["schemas"]["ProductRecord"]["properties"]
    assert "productId" in record_properties
    assert "modelNumber" in record_properties
    assert "entityType" not in record_properties
    assert "requestId" in schema["components"]["schemas"]["ErrorResponse"]["properties"]


def _assert_error(body: dict[str, object], code: str) -> None:
    error = cast(dict[str, object], body["error"])
    assert error["code"] == code
    assert error["message"]
    assert isinstance(error["details"], dict)
    assert UUID(cast(str, body["requestId"]))
