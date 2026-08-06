"""Product create/retrieve API and OpenAPI contract tests."""

from dataclasses import replace
from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.products import get_product_service
from app.core.exceptions import (
    InvalidProductCursorError,
    ProductAlreadyExistsError,
    ProductRepositoryError,
    ProductVersionConflictError,
)
from app.domain.products import Product, ProductPage, ProductStatus
from app.main import app
from app.repositories.products import ProductRepository
from app.services.products import ProductService
from tests.fixtures.products import PRODUCT_ID, SECOND_PRODUCT_ID, UPDATED_AT, make_product


class MemoryProductRepository:
    def __init__(
        self,
        product: Product | None = None,
        error: Exception | None = None,
        update_error: Exception | None = None,
        delete_error: Exception | None = None,
        page: ProductPage | None = None,
    ) -> None:
        self.product = product
        self.error = error
        self.update_error = update_error
        self.delete_error = delete_error
        self.page = page or ProductPage(items=(), next_cursor=None)
        self.list_calls: list[tuple[int, str | None]] = []
        self.status_list_calls: list[tuple[ProductStatus, int, str | None]] = []
        self.update_calls: list[tuple[Product, int]] = []
        self.delete_calls: list[tuple[UUID, int]] = []

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

    def update(self, product: Product, expected_version: int) -> Product:
        self.update_calls.append((product, expected_version))
        if self.update_error is not None:
            raise self.update_error
        self.product = replace(product, updated_at=UPDATED_AT, version=expected_version + 1)
        return self.product

    def delete(self, product_id: UUID, expected_version: int) -> None:
        self.delete_calls.append((product_id, expected_version))
        if self.delete_error is not None:
            raise self.delete_error
        self.product = None


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


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("name", "  Updated pump  ", "Updated pump"),
        ("manufacturer", None, None),
        ("modelNumber", None, None),
        ("category", "INDUCTION_MOTOR", "INDUCTION_MOTOR"),
        ("status", "PROCESSING", "PROCESSING"),
        ("description", "Updated description", "Updated description"),
    ],
)
def test_patch_updates_each_editable_field(
    client: TestClient, field: str, value: object, expected: object
) -> None:
    repository = MemoryProductRepository(product=make_product())
    _override(repository)

    response = client.patch(
        f"/api/v1/products/{PRODUCT_ID}",
        json={"version": 1, field: value},
    )

    assert response.status_code == 200
    assert response.json()[field] == expected
    assert repository.update_calls[0][1] == 1


def test_patch_updates_multiple_fields_and_preserves_system_fields(client: TestClient) -> None:
    current = make_product()
    repository = MemoryProductRepository(product=current)
    _override(repository)

    response = client.patch(
        f"/api/v1/products/{PRODUCT_ID}",
        json={
            "version": 1,
            "manufacturer": None,
            "modelNumber": "PX-500",
            "category": "INDUCTION_MOTOR",
            "status": "REVIEW_REQUIRED",
            "description": "Revised description",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == current.name
    assert body["manufacturer"] is None
    assert body["modelNumber"] == "PX-500"
    assert body["category"] == "INDUCTION_MOTOR"
    assert body["status"] == "REVIEW_REQUIRED"
    assert body["description"] == "Revised description"
    assert body["productId"] == str(current.product_id)
    assert body["createdAt"] == "2026-08-06T11:30:00Z"
    assert body["sourceCount"] == current.source_count
    assert body["version"] == 2
    assert body["updatedAt"] == "2026-08-06T12:00:00Z"
    assert "entityType" not in body


@pytest.mark.parametrize(
    "payload",
    [
        {"version": 1},
        {"name": "Updated name"},
        {"version": 0, "name": "Updated name"},
        {"version": -1, "name": "Updated name"},
        {"version": "abc", "name": "Updated name"},
        {"version": None, "name": "Updated name"},
        {"version": True, "name": "Updated name"},
        {"version": 1, "name": ""},
        {"version": 1, "name": None},
        {"version": 1, "category": "UNKNOWN"},
        {"version": 1, "category": None},
        {"version": 1, "status": "UNKNOWN"},
        {"version": 1, "status": None},
        {"version": 1, "description": "x" * 4_001},
        {"version": 1, "unknownField": "value"},
    ],
)
def test_patch_rejects_invalid_requests(client: TestClient, payload: dict[str, object]) -> None:
    repository = MemoryProductRepository(product=make_product())
    _override(repository)
    response = client.patch(f"/api/v1/products/{PRODUCT_ID}", json=payload)
    assert response.status_code == 422
    _assert_error(response.json(), "REQUEST_VALIDATION_FAILED")
    assert repository.update_calls == []


@pytest.mark.parametrize(
    "field",
    ["productId", "createdAt", "updatedAt", "sourceCount", "entityType"],
)
def test_patch_rejects_immutable_fields(client: TestClient, field: str) -> None:
    repository = MemoryProductRepository(product=make_product())
    _override(repository)
    response = client.patch(
        f"/api/v1/products/{PRODUCT_ID}",
        json={"version": 1, "name": "Updated name", field: "forbidden"},
    )
    assert response.status_code == 422
    _assert_error(response.json(), "REQUEST_VALIDATION_FAILED")
    assert repository.update_calls == []


def test_patch_missing_product_returns_safe_404(client: TestClient) -> None:
    _override(MemoryProductRepository())
    response = client.patch(
        f"/api/v1/products/{PRODUCT_ID}", json={"version": 1, "status": "FAILED"}
    )
    assert response.status_code == 404
    _assert_error(response.json(), "PRODUCT_NOT_FOUND")


def test_patch_stale_version_returns_safe_409(client: TestClient) -> None:
    repository = MemoryProductRepository(
        product=make_product(),
        update_error=ProductVersionConflictError("condition expression detail"),
    )
    _override(repository)
    response = client.patch(
        f"/api/v1/products/{PRODUCT_ID}", json={"version": 1, "status": "FAILED"}
    )
    assert response.status_code == 409
    _assert_error(response.json(), "PRODUCT_VERSION_CONFLICT")
    assert "condition expression detail" not in response.text


def test_patch_repository_failure_returns_safe_503(client: TestClient) -> None:
    repository = MemoryProductRepository(
        product=make_product(), update_error=ProductRepositoryError("secret-table-name")
    )
    _override(repository)
    response = client.patch(
        f"/api/v1/products/{PRODUCT_ID}", json={"version": 1, "status": "FAILED"}
    )
    assert response.status_code == 503
    _assert_error(response.json(), "PRODUCT_STORAGE_UNAVAILABLE")
    assert "secret-table-name" not in response.text


def test_patch_unexpected_failure_returns_safe_500() -> None:
    repository = MemoryProductRepository(
        product=make_product(), update_error=RuntimeError("internal update secret")
    )
    _override(repository)
    try:
        with TestClient(app, raise_server_exceptions=False) as safe_client:
            response = safe_client.patch(
                f"/api/v1/products/{PRODUCT_ID}",
                json={"version": 1, "status": "FAILED"},
            )
        assert response.status_code == 500
        _assert_error(response.json(), "INTERNAL_SERVER_ERROR")
        assert "internal update secret" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_delete_product_returns_empty_204_and_product_cannot_be_retrieved(
    client: TestClient,
) -> None:
    repository = MemoryProductRepository(product=make_product())
    _override(repository)

    response = client.delete(f"/api/v1/products/{PRODUCT_ID}?version=1")

    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["X-Request-ID"]
    assert repository.delete_calls == [(PRODUCT_ID, 1)]
    retrieve = client.get(f"/api/v1/products/{PRODUCT_ID}")
    assert retrieve.status_code == 404
    _assert_error(retrieve.json(), "PRODUCT_NOT_FOUND")


@pytest.mark.parametrize("query", ["", "?version=0", "?version=-1", "?version=abc", "?version="])
def test_delete_rejects_missing_or_invalid_version(client: TestClient, query: str) -> None:
    repository = MemoryProductRepository(product=make_product())
    _override(repository)
    response = client.delete(f"/api/v1/products/{PRODUCT_ID}{query}")
    assert response.status_code == 422
    _assert_error(response.json(), "REQUEST_VALIDATION_FAILED")
    assert repository.delete_calls == []


def test_delete_rejects_invalid_uuid_before_service(client: TestClient) -> None:
    repository = MemoryProductRepository(product=make_product())
    _override(repository)
    response = client.delete("/api/v1/products/not-a-uuid?version=1")
    assert response.status_code == 422
    _assert_error(response.json(), "REQUEST_VALIDATION_FAILED")
    assert repository.delete_calls == []


def test_delete_missing_product_returns_safe_404(client: TestClient) -> None:
    repository = MemoryProductRepository()
    _override(repository)
    response = client.delete(f"/api/v1/products/{PRODUCT_ID}?version=1")
    assert response.status_code == 404
    _assert_error(response.json(), "PRODUCT_NOT_FOUND")
    assert repository.delete_calls == []


def test_delete_stale_version_returns_safe_409_without_deleting(client: TestClient) -> None:
    product = make_product(version=2)
    repository = MemoryProductRepository(
        product=product,
        delete_error=ProductVersionConflictError("condition expression detail"),
    )
    _override(repository)
    response = client.delete(f"/api/v1/products/{PRODUCT_ID}?version=1")
    assert response.status_code == 409
    _assert_error(response.json(), "PRODUCT_VERSION_CONFLICT")
    assert "condition expression detail" not in response.text
    assert repository.product == product


def test_delete_repository_failure_returns_safe_503(client: TestClient) -> None:
    repository = MemoryProductRepository(
        product=make_product(), delete_error=ProductRepositoryError("secret-table-name")
    )
    _override(repository)
    response = client.delete(f"/api/v1/products/{PRODUCT_ID}?version=1")
    assert response.status_code == 503
    _assert_error(response.json(), "PRODUCT_STORAGE_UNAVAILABLE")
    assert "secret-table-name" not in response.text


def test_delete_unexpected_failure_returns_safe_500() -> None:
    repository = MemoryProductRepository(
        product=make_product(), delete_error=RuntimeError("internal delete secret")
    )
    _override(repository)
    try:
        with TestClient(app, raise_server_exceptions=False) as safe_client:
            response = safe_client.delete(f"/api/v1/products/{PRODUCT_ID}?version=1")
        assert response.status_code == 500
        _assert_error(response.json(), "INTERNAL_SERVER_ERROR")
        assert "internal delete secret" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_collection_delete_is_not_available(client: TestClient) -> None:
    _override(MemoryProductRepository(product=make_product()))
    response = client.delete("/api/v1/products?version=1")
    assert response.status_code == 405


def test_put_product_is_not_available(client: TestClient) -> None:
    _override(MemoryProductRepository(product=make_product()))
    response = client.put(f"/api/v1/products/{PRODUCT_ID}", json={"version": 1, "name": "Updated"})
    assert response.status_code == 405


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
    assert set(member) == {"get", "patch", "delete"}
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
    assert member["patch"]["responses"]["200"]
    assert member["patch"]["responses"]["404"]
    assert member["patch"]["responses"]["409"]
    assert member["patch"]["responses"]["422"]
    assert member["patch"]["responses"]["503"]
    assert member["patch"]["parameters"][0]["schema"]["format"] == "uuid"
    assert member["delete"]["responses"]["204"] == {"description": "Successful Response"}
    assert member["delete"]["responses"]["404"]
    assert member["delete"]["responses"]["409"]
    assert member["delete"]["responses"]["422"]
    assert member["delete"]["responses"]["503"]
    delete_parameters = {
        parameter["name"]: parameter for parameter in member["delete"]["parameters"]
    }
    assert set(delete_parameters) == {"product_id", "version"}
    assert delete_parameters["product_id"]["in"] == "path"
    assert delete_parameters["product_id"]["schema"]["format"] == "uuid"
    assert delete_parameters["version"]["in"] == "query"
    assert delete_parameters["version"]["required"] is True
    assert delete_parameters["version"]["schema"]["minimum"] == 1
    update_schema = schema["components"]["schemas"]["ProductUpdate"]
    assert update_schema["required"] == ["version"]
    assert set(update_schema["properties"]) == {
        "version",
        "name",
        "manufacturer",
        "modelNumber",
        "category",
        "status",
        "description",
    }
    for field in ("name", "category", "status"):
        assert not any(
            option.get("type") == "null"
            for option in update_schema["properties"][field].get("anyOf", [])
        )
    for field in ("manufacturer", "modelNumber", "description"):
        assert any(
            option.get("type") == "null" for option in update_schema["properties"][field]["anyOf"]
        )
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
