"""Text product-source API and OpenAPI contract tests."""

import hashlib
import io
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.product_sources import get_product_source_service
from app.core.exceptions import (
    InvalidProductSourceCursorError,
    ObjectStorageError,
    ProductRepositoryError,
    ProductSourceAlreadyExistsError,
    ProductSourceRepositoryError,
    ProductSourceVersionConflictError,
)
from app.domain.product_sources import ProductSourcePage, ProductSourceStatus
from app.main import app
from app.repositories.product_sources import ProductSourceRepository
from app.repositories.products import ProductRepository
from app.services.product_sources import ProductSourceService
from app.storage.keys import METADATA_SUFFIX
from app.storage.local import LocalObjectStorage
from app.storage.protocol import ObjectStorage
from app.utils.file_validation import UploadSizeLimits
from tests.fixtures.product_sources import SECOND_SOURCE_ID, SOURCE_ID, make_product_source
from tests.fixtures.products import PRODUCT_ID, make_product
from tests.unit.test_product_source_service import (
    FakeProductRepository,
    FakeProductSourceRepository,
    FakeStorage,
    text_source,
)


def override_service(
    products: FakeProductRepository,
    sources: FakeProductSourceRepository,
    storage: ObjectStorage | None = None,
) -> None:
    service = ProductSourceService(
        cast(ProductRepository, products),
        cast(ProductSourceRepository, sources),
        storage,
        UploadSizeLimits(pdf=20, image=20, csv=20) if storage is not None else None,
    )
    app.dependency_overrides[get_product_source_service] = lambda: service


def assert_error(body: dict[str, object], code: str) -> None:
    error = cast(dict[str, object], body["error"])
    assert error["code"] == code
    assert error["message"]
    assert isinstance(error["details"], dict)
    assert UUID(cast(str, body["requestId"]))


def test_create_text_source_returns_201_camel_case_ready_record(client: TestClient) -> None:
    products = FakeProductRepository(product=make_product())
    sources = FakeProductSourceRepository()
    override_service(products, sources)
    text = "Model: PX-400\nPressure: 16 bar"

    response = client.post(
        f"/api/v1/products/{PRODUCT_ID}/sources/text",
        json={"displayName": " Supplier Notes ", "textContent": f"  {text}  "},
    )

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["sourceId"])
    assert body["productId"] == str(PRODUCT_ID)
    assert body["sourceType"] == "TEXT"
    assert body["status"] == "READY"
    assert body["originalFilename"] is None
    assert body["storageKey"] is None
    assert body["mimeType"] == "text/plain"
    assert body["fileSizeBytes"] == len(text.encode("utf-8"))
    assert body["checksumSha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert body["displayName"] == "Supplier Notes"
    assert body["textContent"] == text
    assert body["errorMessage"] is None
    assert body["version"] == 1
    assert body["createdAt"].endswith("Z")
    assert body["updatedAt"] == body["createdAt"]
    assert response.headers["X-Request-ID"]
    assert products.requested_ids == [PRODUCT_ID]
    assert len(sources.created) == 1


def test_empty_display_name_returns_null(client: TestClient) -> None:
    override_service(FakeProductRepository(product=make_product()), FakeProductSourceRepository())
    response = client.post(
        f"/api/v1/products/{PRODUCT_ID}/sources/text",
        json={"displayName": "   ", "textContent": "Model PX-400"},
    )
    assert response.status_code == 201
    assert response.json()["displayName"] is None


def test_missing_parent_returns_404_without_source_create(client: TestClient) -> None:
    products = FakeProductRepository()
    sources = FakeProductSourceRepository()
    override_service(products, sources)

    response = client.post(
        f"/api/v1/products/{PRODUCT_ID}/sources/text",
        json={"textContent": "Model PX-400"},
    )

    assert response.status_code == 404
    assert_error(response.json(), "PRODUCT_NOT_FOUND")
    assert response.json()["error"]["details"] == {"productId": str(PRODUCT_ID)}
    assert sources.created == []


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"textContent": ""},
        {"textContent": "   "},
        {"textContent": None},
        {"textContent": 42},
        {"textContent": "x" * 50_001},
        {"textContent": "valid", "unknownField": "rejected"},
        {"textContent": "valid", "sourceId": "f348db3c-4da2-47f8-8716-179b7dd9273c"},
        {"textContent": "valid", "sourceType": "TEXT"},
        {"textContent": "valid", "status": "READY"},
        {"textContent": "valid", "storageKey": "object.txt"},
        {"textContent": "valid", "version": 1},
        {"textContent": "valid", "productId": str(PRODUCT_ID)},
        {"textContent": "valid", "createdAt": "2026-08-06T18:00:00Z"},
    ],
)
def test_invalid_request_is_rejected_before_service(
    client: TestClient, payload: dict[str, object]
) -> None:
    products = FakeProductRepository(product=make_product())
    sources = FakeProductSourceRepository()
    override_service(products, sources)
    response = client.post(f"/api/v1/products/{PRODUCT_ID}/sources/text", json=payload)
    assert response.status_code == 422
    assert_error(response.json(), "REQUEST_VALIDATION_FAILED")
    assert products.requested_ids == []
    assert sources.created == []


def test_invalid_product_uuid_is_rejected_before_service(client: TestClient) -> None:
    products = FakeProductRepository(product=make_product())
    sources = FakeProductSourceRepository()
    override_service(products, sources)
    response = client.post(
        "/api/v1/products/not-a-uuid/sources/text", json={"textContent": "valid"}
    )
    assert response.status_code == 422
    assert_error(response.json(), "REQUEST_VALIDATION_FAILED")
    assert products.requested_ids == []
    assert sources.created == []


def test_duplicate_source_returns_safe_409(client: TestClient) -> None:
    override_service(
        FakeProductRepository(product=make_product()),
        FakeProductSourceRepository(error=ProductSourceAlreadyExistsError("private duplicate")),
    )
    response = client.post(
        f"/api/v1/products/{PRODUCT_ID}/sources/text", json={"textContent": "valid"}
    )
    assert response.status_code == 409
    assert_error(response.json(), "PRODUCT_SOURCE_ALREADY_EXISTS")
    assert "private duplicate" not in response.text


def test_product_repository_failure_returns_safe_503(client: TestClient) -> None:
    override_service(
        FakeProductRepository(error=ProductRepositoryError("private-products-table")),
        FakeProductSourceRepository(),
    )
    response = client.post(
        f"/api/v1/products/{PRODUCT_ID}/sources/text", json={"textContent": "valid"}
    )
    assert response.status_code == 503
    assert_error(response.json(), "PRODUCT_STORAGE_UNAVAILABLE")
    assert "private-products-table" not in response.text


def test_source_repository_failure_returns_safe_503(client: TestClient) -> None:
    override_service(
        FakeProductRepository(product=make_product()),
        FakeProductSourceRepository(error=ProductSourceRepositoryError("private-sources-table")),
    )
    response = client.post(
        f"/api/v1/products/{PRODUCT_ID}/sources/text", json={"textContent": "valid"}
    )
    assert response.status_code == 503
    assert_error(response.json(), "PRODUCT_SOURCE_STORAGE_UNAVAILABLE")
    assert "private-sources-table" not in response.text


def test_unexpected_failure_returns_safe_500_with_matching_request_id() -> None:
    override_service(
        FakeProductRepository(product=make_product()),
        FakeProductSourceRepository(error=RuntimeError("unexpected private detail")),
    )
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                f"/api/v1/products/{PRODUCT_ID}/sources/text",
                json={"textContent": "valid"},
            )
        assert response.status_code == 500
        assert_error(response.json(), "INTERNAL_SERVER_ERROR")
        assert response.json()["requestId"] == response.headers["X-Request-ID"]
        assert "unexpected private detail" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_list_sources_returns_200_camel_case_newest_first_page(client: TestClient) -> None:
    newest = make_product_source(source_id=SECOND_SOURCE_ID)
    older = make_product_source()
    sources = FakeProductSourceRepository(
        page=ProductSourcePage(items=(newest, older), next_cursor="opaque-next")
    )
    override_service(FakeProductRepository(make_product()), sources)

    response = client.get(
        f"/api/v1/products/{PRODUCT_ID}/sources",
        params={"limit": 10, "cursor": "opaque-current"},
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["sourceId"] for item in body["items"]] == [
        str(SECOND_SOURCE_ID),
        str(SOURCE_ID),
    ]
    assert all(item["productId"] == str(PRODUCT_ID) for item in body["items"])
    assert "sourceType" in body["items"][0]
    assert "createdAt" in body["items"][0]
    assert body["nextCursor"] == "opaque-next"
    assert "total" not in body
    assert response.headers["X-Request-ID"]
    assert sources.requested_lists == [(PRODUCT_ID, 10, "opaque-current")]


def test_list_sources_returns_empty_200_page(client: TestClient) -> None:
    sources = FakeProductSourceRepository()
    override_service(FakeProductRepository(make_product()), sources)
    response = client.get(f"/api/v1/products/{PRODUCT_ID}/sources")
    assert response.status_code == 200
    assert response.json() == {"items": [], "nextCursor": None}
    assert sources.requested_lists == [(PRODUCT_ID, 20, None)]


@pytest.mark.parametrize("limit", [1, 100])
def test_list_source_limit_boundaries_are_accepted(client: TestClient, limit: int) -> None:
    sources = FakeProductSourceRepository()
    override_service(FakeProductRepository(make_product()), sources)
    response = client.get(f"/api/v1/products/{PRODUCT_ID}/sources", params={"limit": limit})
    assert response.status_code == 200
    assert sources.requested_lists == [(PRODUCT_ID, limit, None)]


@pytest.mark.parametrize("limit", ["0", "101", "abc"])
def test_invalid_list_source_limit_is_rejected_before_service(
    client: TestClient, limit: str
) -> None:
    products = FakeProductRepository(make_product())
    sources = FakeProductSourceRepository()
    override_service(products, sources)
    response = client.get(f"/api/v1/products/{PRODUCT_ID}/sources", params={"limit": limit})
    assert response.status_code == 422
    assert_error(response.json(), "REQUEST_VALIDATION_FAILED")
    assert products.requested_ids == []
    assert sources.requested_lists == []


@pytest.mark.parametrize("cursor", ["malformed", "cursor-for-another-product"])
def test_invalid_source_cursor_returns_safe_400(client: TestClient, cursor: str) -> None:
    sources = FakeProductSourceRepository(
        error=InvalidProductSourceCursorError("private cursor detail")
    )
    override_service(FakeProductRepository(make_product()), sources)
    response = client.get(f"/api/v1/products/{PRODUCT_ID}/sources", params={"cursor": cursor})
    assert response.status_code == 400
    assert_error(response.json(), "INVALID_PRODUCT_SOURCE_CURSOR")
    assert "private cursor detail" not in response.text


@pytest.mark.parametrize(
    "path",
    [
        f"/api/v1/products/{PRODUCT_ID}/sources",
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}",
    ],
)
def test_source_reads_return_missing_parent_without_source_access(
    client: TestClient, path: str
) -> None:
    sources = FakeProductSourceRepository(source=make_product_source())
    override_service(FakeProductRepository(), sources)
    response = client.get(path)
    assert response.status_code == 404
    assert_error(response.json(), "PRODUCT_NOT_FOUND")
    assert sources.requested_lists == []
    assert sources.requested_gets == []


def test_retrieve_source_returns_product_scoped_record(client: TestClient) -> None:
    source = make_product_source(storage_key="products/logical/source.pdf")
    sources = FakeProductSourceRepository(source=source)
    override_service(FakeProductRepository(make_product()), sources)
    response = client.get(f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["sourceId"] == str(SOURCE_ID)
    assert body["productId"] == str(PRODUCT_ID)
    assert body["storageKey"] == "products/logical/source.pdf"
    assert "file" not in body and "bytes" not in body
    assert sources.requested_gets == [(PRODUCT_ID, SOURCE_ID)]


def test_retrieve_missing_or_wrong_product_source_returns_safe_404(client: TestClient) -> None:
    other_product_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    sources = FakeProductSourceRepository(source=make_product_source())
    override_service(FakeProductRepository(make_product()), sources)
    response = client.get(f"/api/v1/products/{other_product_id}/sources/{SOURCE_ID}")
    assert response.status_code == 404
    assert_error(response.json(), "PRODUCT_SOURCE_NOT_FOUND")
    assert response.json()["error"]["details"] == {
        "productId": str(other_product_id),
        "sourceId": str(SOURCE_ID),
    }
    assert sources.requested_gets == [(other_product_id, SOURCE_ID)]


@pytest.mark.parametrize(
    "path",
    [
        f"/api/v1/products/not-a-uuid/sources/{SOURCE_ID}",
        f"/api/v1/products/{PRODUCT_ID}/sources/not-a-uuid",
    ],
)
def test_invalid_retrieve_uuid_is_rejected_before_service(client: TestClient, path: str) -> None:
    products = FakeProductRepository(make_product())
    sources = FakeProductSourceRepository(source=make_product_source())
    override_service(products, sources)
    response = client.get(path)
    assert response.status_code == 422
    assert_error(response.json(), "REQUEST_VALIDATION_FAILED")
    assert products.requested_ids == []
    assert sources.requested_gets == []


@pytest.mark.parametrize(
    ("product_error", "source_error", "code"),
    [
        (ProductRepositoryError("private product"), None, "PRODUCT_STORAGE_UNAVAILABLE"),
        (
            None,
            ProductSourceRepositoryError("private source"),
            "PRODUCT_SOURCE_STORAGE_UNAVAILABLE",
        ),
    ],
)
def test_source_read_repository_failures_return_safe_503(
    client: TestClient,
    product_error: Exception | None,
    source_error: Exception | None,
    code: str,
) -> None:
    products = FakeProductRepository(make_product(), error=product_error)
    sources = FakeProductSourceRepository(error=source_error)
    override_service(products, sources)
    response = client.get(f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}")
    assert response.status_code == 503
    assert_error(response.json(), code)
    assert "private" not in response.text


def test_source_read_unexpected_failure_returns_safe_500() -> None:
    override_service(
        FakeProductRepository(make_product()),
        FakeProductSourceRepository(error=RuntimeError("private unexpected")),
    )
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}")
        assert response.status_code == 500
        assert_error(response.json(), "INTERNAL_SERVER_ERROR")
        assert response.json()["requestId"] == response.headers["X-Request-ID"]
        assert "private unexpected" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_update_source_returns_200_and_preserves_immutable_metadata(client: TestClient) -> None:
    current = make_product_source(status=ProductSourceStatus.READY, version=1)
    sources = FakeProductSourceRepository(source=current)
    override_service(FakeProductRepository(make_product()), sources)

    response = client.patch(
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}",
        json={"version": 1, "displayName": " Updated Datasheet "},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["displayName"] == "Updated Datasheet"
    assert body["version"] == 2
    assert body["sourceId"] == str(current.source_id)
    assert body["productId"] == str(current.product_id)
    assert body["sourceType"] == current.source_type.value
    assert body["originalFilename"] == current.original_filename
    assert body["storageKey"] == current.storage_key
    assert body["mimeType"] == current.mime_type
    assert body["fileSizeBytes"] == current.file_size_bytes
    assert body["textContent"] == current.text_content
    assert response.headers["X-Request-ID"]
    assert sources.update_calls[0][1] == 1


def test_update_source_status_and_explicit_nulls(client: TestClient) -> None:
    current = make_product_source(
        status=ProductSourceStatus.FAILED,
        display_name="Old",
        error_message="Old error",
    )
    sources = FakeProductSourceRepository(source=current)
    override_service(FakeProductRepository(make_product()), sources)
    response = client.patch(
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}",
        json={
            "version": 1,
            "status": "READY",
            "displayName": None,
            "errorMessage": None,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "READY"
    assert response.json()["displayName"] is None
    assert response.json()["errorMessage"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"version": 1},
        {"version": 0, "displayName": "x"},
        {"version": 1, "status": None},
        {"version": 1, "storageKey": "changed.pdf"},
        {"version": 1, "textContent": "changed"},
        {"version": 1, "sourceType": "TEXT"},
        {"version": 1, "unknown": "changed"},
    ],
)
def test_invalid_update_body_is_rejected_before_service(
    client: TestClient, payload: dict[str, object]
) -> None:
    products = FakeProductRepository(make_product())
    sources = FakeProductSourceRepository(source=make_product_source())
    override_service(products, sources)
    response = client.patch(f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}", json=payload)
    assert response.status_code == 422
    assert_error(response.json(), "REQUEST_VALIDATION_FAILED")
    assert products.requested_ids == []
    assert sources.update_calls == []


def test_invalid_source_status_transition_returns_safe_409(client: TestClient) -> None:
    sources = FakeProductSourceRepository(
        source=make_product_source(status=ProductSourceStatus.READY)
    )
    override_service(FakeProductRepository(make_product()), sources)
    response = client.patch(
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}",
        json={"version": 1, "status": "COMPLETED"},
    )
    assert response.status_code == 409
    assert_error(response.json(), "PRODUCT_SOURCE_STATUS_TRANSITION_INVALID")
    assert response.json()["error"]["details"] == {
        "sourceId": str(SOURCE_ID),
        "currentStatus": "READY",
        "requestedStatus": "COMPLETED",
    }
    assert sources.update_calls == []


@pytest.mark.parametrize(
    ("products", "sources", "product_id", "code"),
    [
        (
            FakeProductRepository(),
            FakeProductSourceRepository(source=make_product_source()),
            PRODUCT_ID,
            "PRODUCT_NOT_FOUND",
        ),
        (
            FakeProductRepository(make_product()),
            FakeProductSourceRepository(),
            PRODUCT_ID,
            "PRODUCT_SOURCE_NOT_FOUND",
        ),
        (
            FakeProductRepository(make_product()),
            FakeProductSourceRepository(source=make_product_source()),
            UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
            "PRODUCT_SOURCE_NOT_FOUND",
        ),
    ],
)
def test_update_source_missing_and_cross_product_are_safe(
    client: TestClient,
    products: FakeProductRepository,
    sources: FakeProductSourceRepository,
    product_id: UUID,
    code: str,
) -> None:
    override_service(products, sources)
    response = client.patch(
        f"/api/v1/products/{product_id}/sources/{SOURCE_ID}",
        json={"version": 1, "displayName": "Updated"},
    )
    assert response.status_code == 404
    assert_error(response.json(), code)
    assert sources.update_calls == []


@pytest.mark.parametrize(
    "path",
    [
        f"/api/v1/products/not-a-uuid/sources/{SOURCE_ID}",
        f"/api/v1/products/{PRODUCT_ID}/sources/not-a-uuid",
    ],
)
def test_update_source_invalid_uuid_is_rejected_before_service(
    client: TestClient, path: str
) -> None:
    products = FakeProductRepository(make_product())
    sources = FakeProductSourceRepository(source=make_product_source())
    override_service(products, sources)
    response = client.patch(path, json={"version": 1, "displayName": "Updated"})
    assert response.status_code == 422
    assert_error(response.json(), "REQUEST_VALIDATION_FAILED")
    assert products.requested_ids == []
    assert sources.update_calls == []


def test_update_source_stale_version_returns_safe_409_without_overwrite(
    client: TestClient,
) -> None:
    current = make_product_source(display_name="Current", version=2)
    sources = FakeProductSourceRepository(
        source=current,
        update_error=ProductSourceVersionConflictError("private condition"),
    )
    override_service(FakeProductRepository(make_product()), sources)
    response = client.patch(
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}",
        json={"version": 1, "displayName": "Stale overwrite"},
    )
    assert response.status_code == 409
    assert_error(response.json(), "PRODUCT_SOURCE_VERSION_CONFLICT")
    assert "private condition" not in response.text
    assert sources.source is current


@pytest.mark.parametrize(
    ("product_error", "source_error", "update_error", "code"),
    [
        (
            ProductRepositoryError("private product"),
            None,
            None,
            "PRODUCT_STORAGE_UNAVAILABLE",
        ),
        (
            None,
            ProductSourceRepositoryError("private source read"),
            None,
            "PRODUCT_SOURCE_STORAGE_UNAVAILABLE",
        ),
        (
            None,
            None,
            ProductSourceRepositoryError("private source update"),
            "PRODUCT_SOURCE_STORAGE_UNAVAILABLE",
        ),
    ],
)
def test_update_source_repository_failures_return_safe_503(
    client: TestClient,
    product_error: Exception | None,
    source_error: Exception | None,
    update_error: Exception | None,
    code: str,
) -> None:
    products = FakeProductRepository(make_product(), error=product_error)
    sources = FakeProductSourceRepository(
        error=source_error,
        source=make_product_source(),
        update_error=update_error,
    )
    override_service(products, sources)
    response = client.patch(
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}",
        json={"version": 1, "displayName": "Updated"},
    )
    assert response.status_code == 503
    assert_error(response.json(), code)
    assert "private" not in response.text


def test_update_source_unexpected_failure_returns_safe_500() -> None:
    override_service(
        FakeProductRepository(make_product()),
        FakeProductSourceRepository(
            source=make_product_source(), update_error=RuntimeError("private unexpected")
        ),
    )
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.patch(
                f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}",
                json={"version": 1, "displayName": "Updated"},
            )
        assert response.status_code == 500
        assert_error(response.json(), "INTERNAL_SERVER_ERROR")
        assert response.json()["requestId"] == response.headers["X-Request-ID"]
        assert "private unexpected" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_delete_text_source_returns_empty_204_and_skips_storage(client: TestClient) -> None:
    storage = FakeStorage()
    sources = FakeProductSourceRepository(source=text_source(version=2))
    override_service(FakeProductRepository(make_product()), sources, cast(ObjectStorage, storage))
    response = client.delete(
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}", params={"version": 2}
    )
    assert response.status_code == 204
    assert response.content == b""
    assert response.headers.get("content-length") in {None, "0"}
    assert storage.deleted == []
    assert sources.delete_calls == [(PRODUCT_ID, SOURCE_ID, 2)]


def test_delete_file_source_returns_empty_204(client: TestClient) -> None:
    key = f"products/{PRODUCT_ID}/sources/{SOURCE_ID}/source.pdf"
    storage = FakeStorage()
    sources = FakeProductSourceRepository(source=make_product_source(storage_key=key, version=3))
    override_service(FakeProductRepository(make_product()), sources, cast(ObjectStorage, storage))
    response = client.delete(
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}", params={"version": 3}
    )
    assert response.status_code == 204
    assert response.content == b""
    assert storage.deleted == [key]
    assert sources.delete_calls == [(PRODUCT_ID, SOURCE_ID, 3)]


@pytest.mark.parametrize("query", [None, "version=0", "version=-1", "version=abc", "version="])
def test_delete_invalid_or_missing_version_is_rejected_before_service(
    client: TestClient, query: str | None
) -> None:
    products = FakeProductRepository(make_product())
    sources = FakeProductSourceRepository(source=text_source())
    override_service(products, sources)
    path = f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}"
    response = client.delete(path if query is None else f"{path}?{query}")
    assert response.status_code == 422
    assert_error(response.json(), "REQUEST_VALIDATION_FAILED")
    assert products.requested_ids == []
    assert sources.delete_calls == []


@pytest.mark.parametrize(
    "path",
    [
        f"/api/v1/products/not-a-uuid/sources/{SOURCE_ID}?version=1",
        f"/api/v1/products/{PRODUCT_ID}/sources/not-a-uuid?version=1",
    ],
)
def test_delete_invalid_uuid_is_rejected_before_service(client: TestClient, path: str) -> None:
    products = FakeProductRepository(make_product())
    sources = FakeProductSourceRepository(source=text_source())
    override_service(products, sources)
    response = client.delete(path)
    assert response.status_code == 422
    assert_error(response.json(), "REQUEST_VALIDATION_FAILED")
    assert products.requested_ids == []
    assert sources.delete_calls == []


@pytest.mark.parametrize(
    ("products", "sources", "product_id", "code"),
    [
        (
            FakeProductRepository(),
            FakeProductSourceRepository(source=text_source()),
            PRODUCT_ID,
            "PRODUCT_NOT_FOUND",
        ),
        (
            FakeProductRepository(make_product()),
            FakeProductSourceRepository(),
            PRODUCT_ID,
            "PRODUCT_SOURCE_NOT_FOUND",
        ),
        (
            FakeProductRepository(make_product()),
            FakeProductSourceRepository(source=text_source()),
            UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
            "PRODUCT_SOURCE_NOT_FOUND",
        ),
    ],
)
def test_delete_missing_and_cross_product_are_safe(
    client: TestClient,
    products: FakeProductRepository,
    sources: FakeProductSourceRepository,
    product_id: UUID,
    code: str,
) -> None:
    storage = FakeStorage()
    override_service(products, sources, cast(ObjectStorage, storage))
    response = client.delete(
        f"/api/v1/products/{product_id}/sources/{SOURCE_ID}", params={"version": 1}
    )
    assert response.status_code == 404
    assert_error(response.json(), code)
    assert storage.deleted == []
    assert sources.delete_calls == []


def test_delete_stale_version_returns_409_without_deletion(client: TestClient) -> None:
    key = f"products/{PRODUCT_ID}/sources/{SOURCE_ID}/source.pdf"
    storage = FakeStorage()
    sources = FakeProductSourceRepository(source=make_product_source(storage_key=key, version=2))
    override_service(FakeProductRepository(make_product()), sources, cast(ObjectStorage, storage))
    response = client.delete(
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}", params={"version": 1}
    )
    assert response.status_code == 409
    assert_error(response.json(), "PRODUCT_SOURCE_VERSION_CONFLICT")
    assert storage.deleted == []
    assert sources.delete_calls == []


def test_delete_storage_failure_returns_safe_503(client: TestClient) -> None:
    key = f"products/{PRODUCT_ID}/sources/{SOURCE_ID}/source.pdf"
    storage = FakeStorage(delete_error=ObjectStorageError("private path"))
    sources = FakeProductSourceRepository(source=make_product_source(storage_key=key))
    override_service(FakeProductRepository(make_product()), sources, cast(ObjectStorage, storage))
    response = client.delete(
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}", params={"version": 1}
    )
    assert response.status_code == 503
    assert_error(response.json(), "OBJECT_STORAGE_UNAVAILABLE")
    assert "private path" not in response.text
    assert sources.delete_calls == []


def test_delete_corrupt_file_metadata_returns_safe_500(client: TestClient) -> None:
    sources = FakeProductSourceRepository(source=make_product_source(storage_key=None))
    override_service(
        FakeProductRepository(make_product()), sources, cast(ObjectStorage, FakeStorage())
    )
    response = client.delete(
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}", params={"version": 1}
    )
    assert response.status_code == 500
    assert_error(response.json(), "INTERNAL_SERVER_ERROR")
    assert sources.delete_calls == []


@pytest.mark.parametrize(
    ("product_error", "source_error", "delete_error", "code"),
    [
        (
            ProductRepositoryError("private product"),
            None,
            None,
            "PRODUCT_STORAGE_UNAVAILABLE",
        ),
        (
            None,
            ProductSourceRepositoryError("private source read"),
            None,
            "PRODUCT_SOURCE_STORAGE_UNAVAILABLE",
        ),
        (
            None,
            None,
            ProductSourceRepositoryError("private source delete"),
            "PRODUCT_SOURCE_STORAGE_UNAVAILABLE",
        ),
    ],
)
def test_delete_repository_failures_return_safe_503(
    client: TestClient,
    product_error: Exception | None,
    source_error: Exception | None,
    delete_error: Exception | None,
    code: str,
) -> None:
    products = FakeProductRepository(make_product(), error=product_error)
    sources = FakeProductSourceRepository(
        error=source_error,
        source=text_source(),
        delete_error=delete_error,
    )
    override_service(products, sources)
    response = client.delete(
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}", params={"version": 1}
    )
    assert response.status_code == 503
    assert_error(response.json(), code)
    assert "private" not in response.text


def test_delete_unexpected_failure_returns_safe_500() -> None:
    sources = FakeProductSourceRepository(
        source=text_source(), delete_error=RuntimeError("private")
    )
    override_service(FakeProductRepository(make_product()), sources)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.delete(
                f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}", params={"version": 1}
            )
        assert response.status_code == 500
        assert_error(response.json(), "INTERNAL_SERVER_ERROR")
        assert response.json()["requestId"] == response.headers["X-Request-ID"]
        assert "private" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_local_storage_delete_api_removes_object_sidecar_and_metadata(
    client: TestClient, tmp_path: Path
) -> None:
    root = tmp_path / "objects"
    storage = LocalObjectStorage(root)
    key = f"products/{PRODUCT_ID}/sources/{SOURCE_ID}/source.pdf"
    storage.save(object_key=key, stream=io.BytesIO(b"%PDF-local"), max_size_bytes=100)
    object_path = root.joinpath(*key.split("/"))
    sidecar_path = object_path.with_name(f"{object_path.name}{METADATA_SUFFIX}")
    sources = FakeProductSourceRepository(source=make_product_source(storage_key=key))
    override_service(FakeProductRepository(make_product()), sources, storage)

    response = client.delete(
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}", params={"version": 1}
    )

    assert response.status_code == 204
    assert not object_path.exists()
    assert not sidecar_path.exists()
    assert sources.source is None

    text_sources = FakeProductSourceRepository(source=text_source())
    override_service(FakeProductRepository(make_product()), text_sources, storage)
    text_response = client.delete(
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}", params={"version": 1}
    )
    assert text_response.status_code == 204
    assert text_sources.source is None


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("put", f"/api/v1/products/{PRODUCT_ID}/sources/{UUID(int=1)}"),
        ("delete", f"/api/v1/products/{PRODUCT_ID}/sources"),
        ("post", f"/api/v1/products/{PRODUCT_ID}/sources"),
        ("get", f"/api/v1/products/{PRODUCT_ID}/sources/{UUID(int=1)}/download"),
        ("post", f"/api/v1/products/{PRODUCT_ID}/sources/{UUID(int=1)}/process"),
        ("post", f"/api/v1/products/{PRODUCT_ID}/sources/{UUID(int=1)}/retry"),
    ],
)
def test_unapproved_source_routes_do_not_exist(client: TestClient, method: str, path: str) -> None:
    response = client.request(method, path, json={"textContent": "valid"})
    assert response.status_code in {404, 405}


def test_openapi_documents_exactly_six_source_operations(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    source_paths = {
        path: operations
        for path, operations in schema["paths"].items()
        if "/sources" in path and not path.endswith("/jobs")
    }
    assert set(source_paths) == {
        "/api/v1/products/{product_id}/sources",
        "/api/v1/products/{product_id}/sources/{source_id}",
        "/api/v1/products/{product_id}/sources/text",
        "/api/v1/products/{product_id}/sources/upload",
    }
    list_operation = source_paths["/api/v1/products/{product_id}/sources"]
    assert set(list_operation) == {"get"}
    list_get = list_operation["get"]
    assert list_get["summary"] == "List product sources"
    assert {parameter["name"] for parameter in list_get["parameters"]} == {
        "product_id",
        "limit",
        "cursor",
    }
    limit_parameter = next(
        parameter for parameter in list_get["parameters"] if parameter["name"] == "limit"
    )
    assert limit_parameter["schema"] == {
        "type": "integer",
        "maximum": 100,
        "minimum": 1,
        "default": 20,
        "title": "Limit",
    }
    assert set(list_get["responses"]) == {"200", "400", "404", "422", "503"}
    list_ref = list_get["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert list_ref.endswith("/ProductSourceListResult")
    item_operations = source_paths["/api/v1/products/{product_id}/sources/{source_id}"]
    assert set(item_operations) == {"get", "patch", "delete"}
    retrieve = item_operations["get"]
    assert retrieve["summary"] == "Retrieve a product source"
    assert {parameter["name"] for parameter in retrieve["parameters"]} == {
        "product_id",
        "source_id",
    }
    assert all(parameter["schema"]["format"] == "uuid" for parameter in retrieve["parameters"])
    assert set(retrieve["responses"]) == {"200", "404", "422", "503"}
    retrieve_ref = retrieve["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert retrieve_ref.endswith("/ProductSourceRecord")
    patch_operation = item_operations["patch"]
    assert patch_operation["summary"] == "Update product source metadata and status"
    assert {parameter["name"] for parameter in patch_operation["parameters"]} == {
        "product_id",
        "source_id",
    }
    assert set(patch_operation["responses"]) == {"200", "404", "409", "422", "503"}
    update_ref = patch_operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    update_schema = schema["components"]["schemas"][update_ref.rsplit("/", 1)[-1]]
    assert update_schema["required"] == ["version"]
    assert set(update_schema["properties"]) == {
        "version",
        "displayName",
        "status",
        "errorMessage",
    }
    assert update_schema["properties"]["version"]["minimum"] == 1
    patch_response_ref = patch_operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    assert patch_response_ref.endswith("/ProductSourceRecord")
    delete_operation = item_operations["delete"]
    assert delete_operation["summary"] == "Delete a product source"
    assert {parameter["name"] for parameter in delete_operation["parameters"]} == {
        "product_id",
        "source_id",
        "version",
    }
    version_parameter = next(
        parameter for parameter in delete_operation["parameters"] if parameter["name"] == "version"
    )
    assert version_parameter["required"] is True
    assert version_parameter["in"] == "query"
    assert version_parameter["schema"]["minimum"] == 1
    assert set(delete_operation["responses"]) == {"204", "404", "409", "422", "503"}
    assert "content" not in delete_operation["responses"]["204"]
    operation = source_paths["/api/v1/products/{product_id}/sources/text"]
    assert set(operation) == {"post"}
    post = operation["post"]
    assert post["summary"] == "Create a text product source"
    assert post["parameters"][0]["name"] == "product_id"
    assert post["parameters"][0]["in"] == "path"
    assert post["parameters"][0]["required"] is True
    assert post["parameters"][0]["schema"]["format"] == "uuid"
    assert set(post["responses"]) == {"201", "404", "409", "422", "503"}
    request_schema = schema["components"]["schemas"]["TextProductSourceCreate"]
    assert request_schema["required"] == ["textContent"]
    assert set(request_schema["properties"]) == {"displayName", "textContent"}
    assert request_schema["properties"]["textContent"]["maxLength"] == 50_000
    response_ref = post["responses"]["201"]["content"]["application/json"]["schema"]["$ref"]
    assert response_ref.endswith("/ProductSourceRecord")
    upload = source_paths["/api/v1/products/{product_id}/sources/upload"]["post"]
    assert set(upload["responses"]) == {"201", "404", "409", "413", "422", "503"}
    body = upload["requestBody"]["content"]["multipart/form-data"]["schema"]
    upload_schema = schema["components"]["schemas"][body["$ref"].rsplit("/", 1)[-1]]
    assert upload_schema["required"] == ["file"]
    assert set(upload_schema["properties"]) == {"file", "displayName"}
    assert upload_schema["properties"]["file"] == {
        "type": "string",
        "contentMediaType": "application/octet-stream",
        "title": "File",
        "description": "PDF, PNG, JPEG, WEBP, or CSV file",
    }


def test_upload_pdf_returns_ready_source(client: TestClient) -> None:
    storage = FakeStorage()
    override_service(
        FakeProductRepository(make_product()),
        FakeProductSourceRepository(),
        cast(ObjectStorage, storage),
    )
    content = b"%PDF-valid"
    response = client.post(
        f"/api/v1/products/{PRODUCT_ID}/sources/upload",
        files={"file": (r"C:\fakepath\Pump.PDF", content, "application/pdf")},
        data={"displayName": "  Datasheet  "},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["sourceType"] == "PDF" and body["status"] == "READY"
    assert body["originalFilename"] == "Pump.pdf"
    assert body["mimeType"] == "application/pdf"
    assert body["fileSizeBytes"] == len(content)
    assert body["checksumSha256"] == hashlib.sha256(content).hexdigest()
    assert body["displayName"] == "Datasheet" and body["textContent"] is None


@pytest.mark.parametrize(
    ("files", "code"),
    [
        ({}, "REQUEST_VALIDATION_FAILED"),
        ({"file": ("", b"%PDF-x", "application/pdf")}, "REQUEST_VALIDATION_FAILED"),
        (
            {"file": ("x.exe", b"x", "application/octet-stream")},
            "UNSUPPORTED_PRODUCT_SOURCE_FILE_TYPE",
        ),
        ({"file": ("x.pdf", b"%PDF-x", "image/png")}, "PRODUCT_SOURCE_MIME_TYPE_MISMATCH"),
        ({"file": ("x.pdf", b"plain", "application/pdf")}, "INVALID_PRODUCT_SOURCE_FILE_CONTENT"),
    ],
)
def test_upload_validation_errors(client: TestClient, files: dict[str, object], code: str) -> None:
    storage = FakeStorage()
    override_service(
        FakeProductRepository(make_product()),
        FakeProductSourceRepository(),
        cast(ObjectStorage, storage),
    )
    response = client.post(f"/api/v1/products/{PRODUCT_ID}/sources/upload", files=files)
    assert response.status_code == 422
    assert_error(response.json(), code)
    assert storage.saved == []


def test_upload_too_large_returns_413(client: TestClient) -> None:
    storage = FakeStorage()
    override_service(
        FakeProductRepository(make_product()),
        FakeProductSourceRepository(),
        cast(ObjectStorage, storage),
    )
    response = client.post(
        f"/api/v1/products/{PRODUCT_ID}/sources/upload",
        files={"file": ("x.pdf", b"%PDF-" + b"x" * 20, "application/pdf")},
    )
    assert response.status_code == 413
    assert_error(response.json(), "PRODUCT_SOURCE_FILE_TOO_LARGE")


def test_upload_missing_product_skips_storage(client: TestClient) -> None:
    storage = FakeStorage()
    override_service(
        FakeProductRepository(), FakeProductSourceRepository(), cast(ObjectStorage, storage)
    )
    response = client.post(
        f"/api/v1/products/{PRODUCT_ID}/sources/upload",
        files={"file": ("x.pdf", b"%PDF-x", "application/pdf")},
    )
    assert response.status_code == 404
    assert storage.saved == []


def test_upload_storage_failure_returns_503(client: TestClient) -> None:
    storage = FakeStorage(error=ObjectStorageError("private path"))
    override_service(
        FakeProductRepository(make_product()),
        FakeProductSourceRepository(),
        cast(ObjectStorage, storage),
    )
    response = client.post(
        f"/api/v1/products/{PRODUCT_ID}/sources/upload",
        files={"file": ("x.pdf", b"%PDF-x", "application/pdf")},
    )
    assert response.status_code == 503
    assert_error(response.json(), "OBJECT_STORAGE_UNAVAILABLE")


def test_local_storage_upload_and_compensation(client: TestClient, tmp_path: Path) -> None:
    root = tmp_path / "objects"
    storage = LocalObjectStorage(root)
    sources = FakeProductSourceRepository()
    override_service(FakeProductRepository(make_product()), sources, storage)
    content = b"%PDF-local-content"
    response = client.post(
        f"/api/v1/products/{PRODUCT_ID}/sources/upload",
        files={"file": ("x.pdf", content, "application/pdf")},
    )
    assert response.status_code == 201
    key = response.json()["storageKey"]
    assert storage.exists(key)
    with storage.open(key) as saved:
        assert saved.read() == content
    assert storage.get_metadata(key).checksum_sha256 == response.json()["checksumSha256"]
    storage.delete(key)

    override_service(
        FakeProductRepository(make_product()),
        FakeProductSourceRepository(ProductSourceRepositoryError("failure")),
        storage,
    )
    failed = client.post(
        f"/api/v1/products/{PRODUCT_ID}/sources/upload",
        files={"file": ("x.pdf", content, "application/pdf")},
    )
    assert failed.status_code == 503
    assert not list(root.rglob("*.pdf"))
    assert not list(root.rglob(".object.tmp-*"))
