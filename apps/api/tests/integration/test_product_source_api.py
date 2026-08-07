"""Text product-source API and OpenAPI contract tests."""

import hashlib
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.product_sources import get_product_source_service
from app.core.exceptions import (
    ObjectStorageError,
    ProductRepositoryError,
    ProductSourceAlreadyExistsError,
    ProductSourceRepositoryError,
)
from app.main import app
from app.repositories.product_sources import ProductSourceRepository
from app.repositories.products import ProductRepository
from app.services.product_sources import ProductSourceService
from app.storage.local import LocalObjectStorage
from app.storage.protocol import ObjectStorage
from app.utils.file_validation import UploadSizeLimits
from tests.fixtures.products import PRODUCT_ID, make_product
from tests.unit.test_product_source_service import (
    FakeProductRepository,
    FakeProductSourceRepository,
    FakeStorage,
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


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", f"/api/v1/products/{PRODUCT_ID}/sources"),
        ("get", f"/api/v1/products/{PRODUCT_ID}/sources/{UUID(int=1)}"),
        ("patch", f"/api/v1/products/{PRODUCT_ID}/sources/{UUID(int=1)}"),
        ("delete", f"/api/v1/products/{PRODUCT_ID}/sources/{UUID(int=1)}"),
        ("post", f"/api/v1/products/{PRODUCT_ID}/sources"),
    ],
)
def test_unapproved_source_routes_do_not_exist(client: TestClient, method: str, path: str) -> None:
    response = client.request(method, path, json={"textContent": "valid"})
    assert response.status_code in {404, 405}


def test_openapi_documents_exactly_two_source_operations(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    source_paths = {
        path: operations for path, operations in schema["paths"].items() if "/sources" in path
    }
    assert set(source_paths) == {
        "/api/v1/products/{product_id}/sources/text",
        "/api/v1/products/{product_id}/sources/upload",
    }
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
