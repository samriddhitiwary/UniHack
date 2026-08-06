"""Product create/retrieve API and OpenAPI contract tests."""

from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.products import get_product_service
from app.core.exceptions import (
    InvalidProductCursorError,
    ProductAlreadyExistsError,
    ProductRepositoryError,
)
from app.domain.products import Product, ProductPage, ProductStatus
from app.main import app
from app.repositories.products import ProductRepository
from app.services.products import ProductService
from tests.fixtures.products import PRODUCT_ID, SECOND_PRODUCT_ID, make_product


class MemoryProductRepository:
    def __init__(
        self,
        product: Product | None = None,
        error: Exception | None = None,
        page: ProductPage | None = None,
    ) -> None:
        self.product = product
        self.error = error
        self.page = page or ProductPage(items=(), next_cursor=None)
        self.list_calls: list[tuple[int, str | None]] = []
        self.status_list_calls: list[tuple[ProductStatus, int, str | None]] = []

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

    def list_products(self, *, limit: int, cursor: str | None = None) -> ProductPage:
        self.list_calls.append((limit, cursor))
        if self.error is not None:
            raise self.error
        return self.page

    def list_by_status(
        self,
        status: ProductStatus,
        *,
        limit: int,
        cursor: str | None = None,
    ) -> ProductPage:
        self.status_list_calls.append((status, limit, cursor))
        if self.error is not None:
            raise self.error
        return self.page


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


def test_list_products_uses_default_limit_and_returns_repository_order(
    client: TestClient,
) -> None:
    newest = make_product(name="Newest product")
    older = make_product(product_id=SECOND_PRODUCT_ID, name="Older product")
    repository = MemoryProductRepository(
        page=ProductPage(items=(newest, older), next_cursor="opaque-next")
    )
    _override(repository)

    response = client.get("/api/v1/products")

    assert response.status_code == 200
    assert repository.list_calls == [(20, None)]
    assert repository.status_list_calls == []
    assert [item["name"] for item in response.json()["items"]] == [
        "Newest product",
        "Older product",
    ]
    assert response.json()["nextCursor"] == "opaque-next"


def test_list_products_passes_custom_limit_and_cursor(client: TestClient) -> None:
    repository = MemoryProductRepository()
    _override(repository)

    response = client.get("/api/v1/products?limit=5&cursor=opaque-current")

    assert response.status_code == 200
    assert repository.list_calls == [(5, "opaque-current")]
    assert response.json() == {"items": [], "nextCursor": None}


@pytest.mark.parametrize("product_status", list(ProductStatus))
def test_list_products_passes_each_supported_status(
    client: TestClient, product_status: ProductStatus
) -> None:
    repository = MemoryProductRepository()
    _override(repository)

    response = client.get(f"/api/v1/products?status={product_status.value}")

    assert response.status_code == 200
    assert repository.list_calls == []
    assert repository.status_list_calls == [(product_status, 20, None)]


@pytest.mark.parametrize("limit", ["0", "-1", "101", "abc"])
def test_list_products_rejects_invalid_limits(client: TestClient, limit: str) -> None:
    repository = MemoryProductRepository()
    _override(repository)
    response = client.get(f"/api/v1/products?limit={limit}")
    assert response.status_code == 422
    _assert_error(response.json(), "REQUEST_VALIDATION_FAILED")
    assert repository.list_calls == []


def test_list_products_rejects_invalid_status(client: TestClient) -> None:
    repository = MemoryProductRepository()
    _override(repository)
    response = client.get("/api/v1/products?status=UNKNOWN")
    assert response.status_code == 422
    _assert_error(response.json(), "REQUEST_VALIDATION_FAILED")
    assert repository.status_list_calls == []


def test_list_products_maps_malformed_cursor_to_safe_400(client: TestClient) -> None:
    repository = MemoryProductRepository(error=InvalidProductCursorError("decoded-key"))
    _override(repository)
    response = client.get("/api/v1/products?cursor=malformed")
    assert response.status_code == 400
    _assert_error(response.json(), "INVALID_PRODUCT_CURSOR")
    assert "decoded-key" not in response.text


def test_list_products_maps_repository_failure_to_safe_503(client: TestClient) -> None:
    repository = MemoryProductRepository(error=ProductRepositoryError("secret-table-name"))
    _override(repository)
    response = client.get("/api/v1/products")
    assert response.status_code == 503
    _assert_error(response.json(), "PRODUCT_STORAGE_UNAVAILABLE")
    assert "secret-table-name" not in response.text


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
    assert set(collection) == {"post", "get"}
    assert set(member) == {"get"}
    assert collection["post"]["responses"]["201"]
    assert collection["post"]["responses"]["409"]
    assert collection["post"]["responses"]["422"]
    assert collection["post"]["responses"]["503"]
    assert collection["get"]["responses"]["200"]
    assert collection["get"]["responses"]["400"]
    assert collection["get"]["responses"]["422"]
    assert collection["get"]["responses"]["503"]
    parameters = {parameter["name"]: parameter for parameter in collection["get"]["parameters"]}
    assert set(parameters) == {"limit", "cursor", "status"}
    assert parameters["limit"]["required"] is False
    assert parameters["limit"]["schema"] == {
        "type": "integer",
        "maximum": 100,
        "minimum": 1,
        "default": 20,
        "title": "Limit",
    }
    assert parameters["cursor"]["required"] is False
    assert parameters["status"]["required"] is False
    assert member["get"]["responses"]["200"]
    assert member["get"]["responses"]["404"]
    assert member["get"]["responses"]["422"]
    assert member["get"]["responses"]["503"]
    assert member["get"]["parameters"][0]["schema"]["format"] == "uuid"
    category_schema = schema["components"]["schemas"]["ProductCategory"]
    assert category_schema["enum"] == ["UNCLASSIFIED", "CENTRIFUGAL_PUMP", "INDUCTION_MOTOR"]
    status_schema = schema["components"]["schemas"]["ProductStatus"]
    assert status_schema["enum"] == [status.value for status in ProductStatus]
    list_properties = schema["components"]["schemas"]["ProductListResult"]["properties"]
    assert set(list_properties) == {"items", "nextCursor"}
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
