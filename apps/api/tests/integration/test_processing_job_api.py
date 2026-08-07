"""Processing-job create/read API and OpenAPI contract tests."""

from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.processing_jobs import get_processing_job_service
from app.core.exceptions import (
    InvalidProcessingJobCursorError,
    ProcessingJobAlreadyExistsError,
    ProcessingJobNotFoundError,
    ProcessingJobRepositoryError,
    ProcessingJobTypeNotSupportedForSourceError,
    ProductNotFoundError,
    ProductRepositoryError,
    ProductSourceNotFoundError,
    ProductSourceRepositoryError,
)
from app.domain.processing_jobs import ProcessingJob, ProcessingJobType
from app.main import app
from app.schemas.processing_jobs import ProcessingJobListResult, ProcessingJobRecord
from app.services.processing_jobs import ProcessingJobService
from tests.fixtures.processing_jobs import JOB_ID, SECOND_JOB_ID, make_processing_job
from tests.fixtures.product_sources import SOURCE_ID
from tests.fixtures.products import PRODUCT_ID


class StubProcessingJobService:
    def __init__(
        self,
        *,
        job: ProcessingJob | None = None,
        list_result: ProcessingJobListResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.job = job or make_processing_job()
        self.list_result = list_result or ProcessingJobListResult(items=[], next_cursor=None)
        self.error = error
        self.create_calls: list[tuple[UUID, UUID, ProcessingJobType]] = []
        self.get_calls: list[UUID] = []
        self.product_list_calls: list[tuple[UUID, int, str | None]] = []
        self.source_list_calls: list[tuple[UUID, UUID, int, str | None]] = []

    def create_job(
        self, *, product_id: UUID, source_id: UUID, job_type: ProcessingJobType
    ) -> ProcessingJob:
        self.create_calls.append((product_id, source_id, job_type))
        self._raise_if_configured()
        return self.job

    def get_job(self, *, job_id: UUID) -> ProcessingJob:
        self.get_calls.append(job_id)
        self._raise_if_configured()
        return self.job

    def list_product_jobs(
        self, *, product_id: UUID, limit: int, cursor: str | None = None
    ) -> ProcessingJobListResult:
        self.product_list_calls.append((product_id, limit, cursor))
        self._raise_if_configured()
        return self.list_result

    def list_source_jobs(
        self,
        *,
        product_id: UUID,
        source_id: UUID,
        limit: int,
        cursor: str | None = None,
    ) -> ProcessingJobListResult:
        self.source_list_calls.append((product_id, source_id, limit, cursor))
        self._raise_if_configured()
        return self.list_result

    def _raise_if_configured(self) -> None:
        if self.error is not None:
            raise self.error


def override_service(service: StubProcessingJobService) -> None:
    app.dependency_overrides[get_processing_job_service] = lambda: cast(
        ProcessingJobService, service
    )


def assert_error(body: dict[str, object], code: str) -> None:
    error = cast(dict[str, object], body["error"])
    assert error["code"] == code
    assert set(error) == {"code", "message", "details"}
    assert body["requestId"]


def test_create_returns_201_pending_safe_record(client: TestClient) -> None:
    service = StubProcessingJobService()
    override_service(service)
    response = client.post(
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}/jobs",
        json={"jobType": "PDF_TEXT_EXTRACTION"},
    )
    assert response.status_code == 201
    assert service.create_calls == [(PRODUCT_ID, SOURCE_ID, ProcessingJobType.PDF_TEXT_EXTRACTION)]
    body = response.json()
    assert body["jobId"] == str(JOB_ID)
    assert body["productId"] == str(PRODUCT_ID) and body["sourceId"] == str(SOURCE_ID)
    assert (body["status"], body["attempt"], body["progressPercent"], body["version"]) == (
        "PENDING",
        1,
        0,
        1,
    )
    assert body["startedAt"] is body["completedAt"] is None
    assert "sourceScope" not in body


@pytest.mark.parametrize(
    "path",
    [
        f"/api/v1/products/not-a-uuid/sources/{SOURCE_ID}/jobs",
        f"/api/v1/products/{PRODUCT_ID}/sources/not-a-uuid/jobs",
    ],
)
def test_create_rejects_invalid_path_uuids(client: TestClient, path: str) -> None:
    service = StubProcessingJobService()
    override_service(service)
    response = client.post(path, json={"jobType": "SOURCE_PROCESSING"})
    assert response.status_code == 422
    assert_error(response.json(), "REQUEST_VALIDATION_FAILED")
    assert service.create_calls == []


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"jobType": "UNKNOWN"},
        {"jobType": "SOURCE_PROCESSING", "jobId": str(JOB_ID)},
        {"jobType": "SOURCE_PROCESSING", "status": "PENDING"},
        {"jobType": "SOURCE_PROCESSING", "progressPercent": 0},
        {"jobType": "SOURCE_PROCESSING", "version": 1},
        {"job_type": "SOURCE_PROCESSING"},
    ],
)
def test_create_rejects_invalid_or_system_fields(
    client: TestClient, payload: dict[str, object]
) -> None:
    override_service(StubProcessingJobService())
    response = client.post(f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}/jobs", json=payload)
    assert response.status_code == 422
    assert_error(response.json(), "REQUEST_VALIDATION_FAILED")


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (ProductNotFoundError(PRODUCT_ID), 404, "PRODUCT_NOT_FOUND"),
        (
            ProductSourceNotFoundError(PRODUCT_ID, SOURCE_ID),
            404,
            "PRODUCT_SOURCE_NOT_FOUND",
        ),
        (
            ProcessingJobTypeNotSupportedForSourceError("IMAGE", "PDF_TEXT_EXTRACTION"),
            422,
            "PROCESSING_JOB_TYPE_NOT_SUPPORTED",
        ),
        (
            ProcessingJobAlreadyExistsError("collision"),
            409,
            "PROCESSING_JOB_ALREADY_EXISTS",
        ),
    ],
)
def test_create_maps_controlled_errors(
    client: TestClient, error: Exception, status: int, code: str
) -> None:
    override_service(StubProcessingJobService(error=error))
    response = client.post(
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}/jobs",
        json={"jobType": "SOURCE_PROCESSING"},
    )
    assert response.status_code == status
    assert_error(response.json(), code)
    if code == "PROCESSING_JOB_TYPE_NOT_SUPPORTED":
        assert response.json()["error"]["details"] == {
            "sourceType": "IMAGE",
            "jobType": "PDF_TEXT_EXTRACTION",
        }


def test_retrieve_returns_200_without_internal_scope(client: TestClient) -> None:
    service = StubProcessingJobService()
    override_service(service)
    response = client.get(f"/api/v1/processing-jobs/{JOB_ID}")
    assert response.status_code == 200 and service.get_calls == [JOB_ID]
    assert response.json()["jobId"] == str(JOB_ID)
    assert "sourceScope" not in response.json()


def test_retrieve_missing_and_invalid_jobs_are_safe(client: TestClient) -> None:
    override_service(StubProcessingJobService(error=ProcessingJobNotFoundError(JOB_ID)))
    missing = client.get(f"/api/v1/processing-jobs/{JOB_ID}")
    assert missing.status_code == 404
    assert_error(missing.json(), "PROCESSING_JOB_NOT_FOUND")
    assert missing.json()["error"]["details"] == {"jobId": str(JOB_ID)}

    invalid = client.get("/api/v1/processing-jobs/not-a-uuid")
    assert invalid.status_code == 422
    assert_error(invalid.json(), "REQUEST_VALIDATION_FAILED")


def test_product_list_passes_default_and_custom_pagination(client: TestClient) -> None:
    result = ProcessingJobListResult(
        items=[ProcessingJobRecord.model_validate(make_processing_job())],
        next_cursor="opaque-next",
    )
    service = StubProcessingJobService(list_result=result)
    override_service(service)
    default = client.get(f"/api/v1/products/{PRODUCT_ID}/processing-jobs")
    custom = client.get(
        f"/api/v1/products/{PRODUCT_ID}/processing-jobs?limit=7&cursor=opaque-current"
    )
    assert default.status_code == custom.status_code == 200
    assert service.product_list_calls == [
        (PRODUCT_ID, 20, None),
        (PRODUCT_ID, 7, "opaque-current"),
    ]
    assert default.json()["nextCursor"] == "opaque-next"
    assert "total" not in default.json()


def test_source_list_passes_scoped_pagination_and_empty_shape(client: TestClient) -> None:
    service = StubProcessingJobService()
    override_service(service)
    response = client.get(
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}/jobs?limit=4&cursor=opaque"
    )
    assert response.status_code == 200
    assert service.source_list_calls == [(PRODUCT_ID, SOURCE_ID, 4, "opaque")]
    assert response.json() == {"items": [], "nextCursor": None}


@pytest.mark.parametrize("value", ["0", "101", "abc"])
@pytest.mark.parametrize(
    "path",
    [
        f"/api/v1/products/{PRODUCT_ID}/processing-jobs",
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}/jobs",
    ],
)
def test_lists_reject_invalid_limits(client: TestClient, value: str, path: str) -> None:
    override_service(StubProcessingJobService())
    response = client.get(path, params={"limit": value})
    assert response.status_code == 422
    assert_error(response.json(), "REQUEST_VALIDATION_FAILED")


@pytest.mark.parametrize(
    "path",
    [
        f"/api/v1/products/{PRODUCT_ID}/processing-jobs",
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}/jobs",
    ],
)
def test_list_cursor_failures_return_safe_400(client: TestClient, path: str) -> None:
    override_service(
        StubProcessingJobService(error=InvalidProcessingJobCursorError("raw cursor detail"))
    )
    response = client.get(path, params={"cursor": "malformed"})
    assert response.status_code == 400
    assert_error(response.json(), "INVALID_PROCESSING_JOB_CURSOR")
    assert "raw cursor detail" not in response.text


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (ProductRepositoryError("product-table"), "PRODUCT_STORAGE_UNAVAILABLE"),
        (
            ProductSourceRepositoryError("source-table"),
            "PRODUCT_SOURCE_STORAGE_UNAVAILABLE",
        ),
        (
            ProcessingJobRepositoryError("job-table"),
            "PROCESSING_JOB_STORAGE_UNAVAILABLE",
        ),
    ],
)
def test_repository_failures_return_safe_503(
    client: TestClient, error: Exception, code: str
) -> None:
    override_service(StubProcessingJobService(error=error))
    response = client.post(
        f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}/jobs",
        json={"jobType": "SOURCE_PROCESSING"},
    )
    assert response.status_code == 503
    assert_error(response.json(), code)
    assert "table" not in response.text


def test_unexpected_failure_returns_safe_500() -> None:
    override_service(StubProcessingJobService(error=RuntimeError("private detail")))
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(f"/api/v1/processing-jobs/{JOB_ID}")
        assert response.status_code == 500
        assert_error(response.json(), "INTERNAL_SERVER_ERROR")
        assert "private detail" not in response.text
        assert response.headers["X-Request-ID"] == response.json()["requestId"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("patch", f"/api/v1/processing-jobs/{JOB_ID}"),
        ("delete", f"/api/v1/processing-jobs/{JOB_ID}"),
        ("post", f"/api/v1/processing-jobs/{JOB_ID}/start"),
        ("post", f"/api/v1/processing-jobs/{JOB_ID}/cancel"),
        ("post", f"/api/v1/processing-jobs/{JOB_ID}/retry"),
        ("get", "/api/v1/processing-jobs"),
        ("get", f"/api/v1/products/{PRODUCT_ID}/sources/{SOURCE_ID}/jobs/{SECOND_JOB_ID}"),
    ],
)
def test_unapproved_job_routes_do_not_exist(client: TestClient, method: str, path: str) -> None:
    override_service(StubProcessingJobService())
    response = client.request(method, path, json={})
    assert response.status_code in {404, 405}


def test_openapi_documents_exactly_four_processing_job_operations(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    expected = {
        "/api/v1/products/{product_id}/sources/{source_id}/jobs": {"post", "get"},
        "/api/v1/processing-jobs/{job_id}": {"get"},
        "/api/v1/products/{product_id}/processing-jobs": {"get"},
    }
    paths = {path: schema["paths"][path] for path in expected}
    assert sum(len(operations) for operations in paths.values()) == 4
    assert {path: set(operations) for path, operations in paths.items()} == expected

    create = paths["/api/v1/products/{product_id}/sources/{source_id}/jobs"]["post"]
    assert create["summary"] == "Create a processing job"
    assert set(create["responses"]) == {"201", "404", "409", "422", "503"}
    request_ref = create["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    request_schema = schema["components"]["schemas"][request_ref.rsplit("/", 1)[-1]]
    assert request_schema["required"] == ["jobType"]
    assert set(request_schema["properties"]) == {"jobType"}
    job_type_ref = request_schema["properties"]["jobType"]["$ref"]
    assert schema["components"]["schemas"][job_type_ref.rsplit("/", 1)[-1]]["enum"] == [
        job_type.value for job_type in ProcessingJobType
    ]
    assert all(parameter["schema"]["format"] == "uuid" for parameter in create["parameters"])

    retrieve = paths["/api/v1/processing-jobs/{job_id}"]["get"]
    assert set(retrieve["responses"]) == {"200", "404", "422", "503"}
    for path in (
        "/api/v1/products/{product_id}/processing-jobs",
        "/api/v1/products/{product_id}/sources/{source_id}/jobs",
    ):
        listing = paths[path]["get"]
        assert set(listing["responses"]) == {"200", "400", "404", "422", "503"}
        limit = next(item for item in listing["parameters"] if item["name"] == "limit")
        assert limit["schema"]["default"] == 20
        assert limit["schema"]["minimum"] == 1 and limit["schema"]["maximum"] == 100

    assert "patch" not in paths["/api/v1/processing-jobs/{job_id}"]
    assert "delete" not in paths["/api/v1/processing-jobs/{job_id}"]
    assert "/api/v1/processing-jobs" not in schema["paths"]
