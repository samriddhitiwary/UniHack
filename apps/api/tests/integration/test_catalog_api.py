"""SPEC-032 catalog projection and publishing-readiness API tests."""

from dataclasses import replace
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.catalog import get_publishing_readiness_service
from app.core.exceptions import CatalogProjectionRepositoryError, ProductRepositoryError
from app.domain.catalog_projection import (
    CatalogBlockingReason,
    CatalogProjectionStatus,
    CommerceCatalogProjection,
)
from app.domain.products import Product, ProductPage, ProductStatus
from app.main import app
from app.repositories.catalog_projection import CommerceCatalogProjectionRepository
from app.repositories.products import ProductRepository
from app.services.publishing_readiness_application import (
    PublishingReadinessApplicationService,
)
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.catalog_projection import projected_result


class ApiProducts:
    def __init__(
        self,
        product: Product | None,
        *,
        read_error: Exception | None = None,
        transition_error: Exception | None = None,
    ) -> None:
        self.product = product
        self.read_error = read_error
        self.transition_error = transition_error
        self.transitions = 0

    def get_by_id(self, product_id: UUID) -> Product | None:
        if self.read_error:
            raise self.read_error
        return self.product if self.product and self.product.product_id == product_id else None

    def mark_ready_to_publish(
        self, *, product_id: UUID, expected_version: int, expected_status: ProductStatus
    ) -> Product:
        self.transitions += 1
        if self.transition_error:
            raise self.transition_error
        assert self.product is not None
        self.product = replace(
            self.product,
            status=ProductStatus.READY_TO_PUBLISH,
            version=expected_version + 1,
            updated_at=NOW,
        )
        return self.product

    def create(self, product):  # pragma: no cover - protocol-only
        return product

    def update(self, product, expected_version):  # pragma: no cover
        return product

    def list_products(self, *, limit=25, cursor=None):  # pragma: no cover
        return ProductPage(items=(), next_cursor=None)

    def list_by_status(self, status, *, limit=25, cursor=None):  # pragma: no cover
        return ProductPage(items=(), next_cursor=None)

    def delete(self, product_id, expected_version):  # pragma: no cover
        return None


class ApiProjections:
    def __init__(
        self,
        projection: CommerceCatalogProjection | None,
        error: Exception | None = None,
    ) -> None:
        self.projection = projection
        self.error = error

    def get_by_id(self, projection_id: UUID) -> CommerceCatalogProjection | None:
        if self.error:
            raise self.error
        return (
            self.projection
            if self.projection and self.projection.projection_id == projection_id
            else None
        )

    def create(self, result):  # pragma: no cover - protocol-only
        return result

    def get_by_job_id(self, job_id):  # pragma: no cover
        return None

    def get_by_materialization_id(self, materialization_id):  # pragma: no cover
        return None


def _override(
    product: Product | None,
    projection: CommerceCatalogProjection | None,
    *,
    product_error: Exception | None = None,
    projection_error: Exception | None = None,
    transition_error: Exception | None = None,
) -> ApiProducts:
    products = ApiProducts(product, read_error=product_error, transition_error=transition_error)
    projections = ApiProjections(projection, projection_error)
    service = PublishingReadinessApplicationService(
        cast(ProductRepository, products),
        cast(CommerceCatalogProjectionRepository, projections),
    )
    app.dependency_overrides[get_publishing_readiness_service] = lambda: service
    return products


def test_catalog_get_returns_compact_identity_attributes_reasons_and_lineage(
    client: TestClient,
) -> None:
    product, _, projection = projected_result(manufacturer=None)
    _override(product, projection)
    response = client.get(
        f"/api/v1/products/{product.product_id}/catalog-projections/{projection.projection_id}"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["productName"] == projection.product_name
    assert body["productVersion"] == 3
    assert body["status"] == "READY_WITH_WARNINGS"
    assert body["warningReasonCodes"] == ["MANUFACTURER_MISSING"]
    assert body["materializationId"] == str(projection.materialization_id)
    assert body["attributes"][0]["reviewDecisionId"]
    assert "rawEvidence" not in response.text
    assert response.headers["X-Request-ID"]


def test_readiness_get_returns_current_eligible_state(client: TestClient) -> None:
    product, _, projection = projected_result()
    _override(product, projection)
    response = client.get(
        f"/api/v1/products/{product.product_id}/catalog-projections/"
        f"{projection.projection_id}/readiness"
    )
    assert response.status_code == 200
    assert response.json() == {
        "productId": str(product.product_id),
        "projectionId": str(projection.projection_id),
        "projectionStatus": "READY",
        "blockingReasonCodes": [],
        "warningReasonCodes": [],
        "productVersionAtProjection": 3,
        "currentProductVersion": 3,
        "projectionCurrent": True,
        "eligibleForReadyToPublish": True,
        "currentProductStatus": "REVIEW_REQUIRED",
    }


def test_readiness_get_returns_200_for_stale_and_blocked_states(client: TestClient) -> None:
    product, _, projection = projected_result()
    _override(replace(product, version=4), projection)
    stale = client.get(
        f"/api/v1/products/{product.product_id}/catalog-projections/"
        f"{projection.projection_id}/readiness"
    )
    assert stale.status_code == 200
    assert stale.json()["projectionCurrent"] is False
    assert stale.json()["eligibleForReadyToPublish"] is False

    blocked = replace(
        projection,
        status=CatalogProjectionStatus.BLOCKED,
        blocking_reason_codes=(CatalogBlockingReason.REQUIRED_ATTRIBUTE_MISSING,),
    )
    _override(product, blocked)
    response = client.get(
        f"/api/v1/products/{product.product_id}/catalog-projections/"
        f"{blocked.projection_id}/readiness"
    )
    assert response.status_code == 200
    assert response.json()["blockingReasonCodes"] == ["REQUIRED_ATTRIBUTE_MISSING"]
    assert response.json()["eligibleForReadyToPublish"] is False


@pytest.mark.parametrize("manufacturer", ["CatalogIQ Manufacturing", None])
def test_apply_ready_and_ready_with_warnings_returns_transition(
    client: TestClient, manufacturer: str | None
) -> None:
    product, _, projection = projected_result(manufacturer=manufacturer)
    products = _override(product, projection)
    response = client.post(
        f"/api/v1/products/{product.product_id}/publishing-readiness/apply",
        json={"projectionId": str(projection.projection_id), "version": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["previousStatus"] == "REVIEW_REQUIRED"
    assert body["status"] == "READY_TO_PUBLISH"
    assert (body["previousVersion"], body["version"]) == (3, 4)
    assert body["projectionStatus"] == projection.status.value
    assert body["warningReasonCodes"] == [
        reason.value for reason in projection.warning_reason_codes
    ]
    assert products.transitions == 1


def test_blocked_apply_returns_409_with_bounded_reasons(client: TestClient) -> None:
    product, _, projection = projected_result()
    blocked = replace(
        projection,
        status=CatalogProjectionStatus.BLOCKED,
        blocking_reason_codes=(CatalogBlockingReason.REQUIRED_ATTRIBUTE_INVALID,),
    )
    products = _override(product, blocked)
    response = client.post(
        f"/api/v1/products/{product.product_id}/publishing-readiness/apply",
        json={"projectionId": str(blocked.projection_id), "version": 3},
    )
    _assert_error(response, 409, "PUBLISHING_READINESS_BLOCKED")
    assert response.json()["error"]["details"]["blockingReasonCodes"] == [
        "REQUIRED_ATTRIBUTE_INVALID"
    ]
    assert products.transitions == 0


def test_apply_distinguishes_stale_request_and_projection(client: TestClient) -> None:
    product, _, projection = projected_result()
    _override(product, projection)
    stale_request = client.post(
        f"/api/v1/products/{product.product_id}/publishing-readiness/apply",
        json={"projectionId": str(projection.projection_id), "version": 2},
    )
    _assert_error(stale_request, 409, "PRODUCT_VERSION_CONFLICT")

    _override(replace(product, version=4), projection)
    stale_projection = client.post(
        f"/api/v1/products/{product.product_id}/publishing-readiness/apply",
        json={"projectionId": str(projection.projection_id), "version": 4},
    )
    _assert_error(stale_projection, 409, "PUBLISHING_READINESS_PRODUCT_CHANGED")


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (ProductStatus.DRAFT, "PUBLISHING_READINESS_STATUS_TRANSITION_NOT_ALLOWED"),
        (ProductStatus.PROCESSING, "PUBLISHING_READINESS_STATUS_TRANSITION_NOT_ALLOWED"),
        (ProductStatus.FAILED, "PUBLISHING_READINESS_STATUS_TRANSITION_NOT_ALLOWED"),
        (ProductStatus.READY_TO_PUBLISH, "PRODUCT_ALREADY_READY_TO_PUBLISH"),
    ],
)
def test_apply_rejects_forbidden_product_lifecycle_states(
    client: TestClient, status: ProductStatus, code: str
) -> None:
    product, _, projection = projected_result()
    _override(replace(product, status=status), projection)
    response = client.post(
        f"/api/v1/products/{product.product_id}/publishing-readiness/apply",
        json={"projectionId": str(projection.projection_id), "version": 3},
    )
    _assert_error(response, 409, code)


def test_cross_product_reads_are_isolated_but_apply_is_explicit_422(client: TestClient) -> None:
    product, _, projection = projected_result()
    other = replace(projection, product_id=uuid4())
    _override(product, other)
    get_response = client.get(
        f"/api/v1/products/{product.product_id}/catalog-projections/{other.projection_id}"
    )
    _assert_error(get_response, 404, "CATALOG_PROJECTION_NOT_FOUND")
    readiness = client.get(
        f"/api/v1/products/{product.product_id}/catalog-projections/{other.projection_id}/readiness"
    )
    _assert_error(readiness, 404, "CATALOG_PROJECTION_NOT_FOUND")
    apply = client.post(
        f"/api/v1/products/{product.product_id}/publishing-readiness/apply",
        json={"projectionId": str(other.projection_id), "version": 3},
    )
    _assert_error(apply, 422, "PUBLISHING_READINESS_CROSS_PRODUCT_PROJECTION")


def test_missing_product_and_projection_return_standard_404(client: TestClient) -> None:
    product, _, projection = projected_result()
    _override(None, projection)
    missing_product = client.get(
        f"/api/v1/products/{product.product_id}/catalog-projections/{projection.projection_id}"
    )
    _assert_error(missing_product, 404, "PRODUCT_NOT_FOUND")
    _override(product, None)
    missing_projection = client.get(
        f"/api/v1/products/{product.product_id}/catalog-projections/{uuid4()}"
    )
    _assert_error(missing_projection, 404, "CATALOG_PROJECTION_NOT_FOUND")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"projectionId": "not-a-uuid", "version": 3},
        {"projectionId": str(uuid4()), "version": 0},
        {"projectionId": str(uuid4()), "version": True},
        {"projectionId": str(uuid4()), "version": 3, "extra": "forbidden"},
    ],
)
def test_apply_validation_uses_request_id_error_envelope(
    client: TestClient, payload: dict[str, object]
) -> None:
    product, _, projection = projected_result()
    _override(product, projection)
    response = client.post(
        f"/api/v1/products/{product.product_id}/publishing-readiness/apply",
        json=payload,
        headers={"X-Request-ID": "spec032-request"},
    )
    _assert_error(response, 422, "REQUEST_VALIDATION_FAILED")
    request_id = response.json()["requestId"]
    assert UUID(request_id)
    assert response.headers["X-Request-ID"] == request_id


def test_storage_failures_are_safely_mapped(client: TestClient) -> None:
    product, _, projection = projected_result()
    _override(product, projection, product_error=ProductRepositoryError("secret table"))
    product_failure = client.get(
        f"/api/v1/products/{product.product_id}/catalog-projections/{projection.projection_id}"
    )
    _assert_error(product_failure, 503, "PRODUCT_STORAGE_UNAVAILABLE")
    assert "secret table" not in product_failure.text

    _override(
        product,
        projection,
        projection_error=CatalogProjectionRepositoryError("secret partition"),
    )
    projection_failure = client.get(
        f"/api/v1/products/{product.product_id}/catalog-projections/{projection.projection_id}"
    )
    _assert_error(projection_failure, 503, "CATALOG_PROJECTION_STORAGE_UNAVAILABLE")
    assert "secret partition" not in projection_failure.text

    _override(
        product,
        projection,
        transition_error=ProductRepositoryError("conditional update secret"),
    )
    transition_failure = client.post(
        f"/api/v1/products/{product.product_id}/publishing-readiness/apply",
        json={"projectionId": str(projection.projection_id), "version": 3},
    )
    _assert_error(transition_failure, 503, "PRODUCT_STORAGE_UNAVAILABLE")
    assert "conditional update secret" not in transition_failure.text


def test_openapi_documents_only_the_three_spec_032_operations(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    catalog = "/api/v1/products/{product_id}/catalog-projections/{projection_id}"
    readiness = catalog + "/readiness"
    apply = "/api/v1/products/{product_id}/publishing-readiness/apply"
    assert set(schema["paths"][catalog]) == {"get"}
    assert set(schema["paths"][readiness]) == {"get"}
    assert set(schema["paths"][apply]) == {"post"}
    request_schema = schema["components"]["schemas"]["ApplyPublishingReadinessRequest"]
    assert request_schema["required"] == ["projectionId", "version"]


def _assert_error(response, status: int, code: str) -> None:
    assert response.status_code == status
    body = response.json()
    assert body["error"]["code"] == code
    assert set(body) == {"error", "requestId"}
    assert response.headers["X-Request-ID"] == body["requestId"]
