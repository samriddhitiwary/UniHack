"""Product-review route, validation, error envelope, and request-ID tests."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.product_reviews import get_product_review_service
from app.core.exceptions import (
    ProductReviewManualOverrideInvalidError,
    ProductReviewNotFoundError,
    ProductReviewRepositoryError,
    ProductReviewVersionConflictError,
)
from app.domain.product_review import (
    AttributeReviewDecision,
    AttributeReviewDecisionType,
    ProductReviewSession,
    ReviewDecisionPage,
)
from app.main import app
from tests.fixtures.attribute_normalization import NOW
from tests.unit.test_attribute_selection_engine import pipeline


def records():
    *_, selection = pipeline(("voltage", "415", "V"))
    review = ProductReviewSession.create(selection, NOW)
    decision = AttributeReviewDecision(
        decision_id=uuid4(),
        review_id=review.review_id,
        product_id=review.product_id,
        decision_sequence=1,
        attribute_name="voltage",
        decision_type=AttributeReviewDecisionType.MANUAL_OVERRIDE,
        candidate_id=None,
        approved_value="430",
        approved_unit="V",
        manual_raw_value="430",
        manual_raw_unit="V",
        comment=None,
        reviewer_id="reviewer-local-001",
        review_version=2,
        created_at=NOW,
    )
    ready = replace(
        review,
        required_resolved_count=review.required_attribute_count,
        required_unresolved_count=0,
    )
    completed = ready.complete(NOW + timedelta(seconds=1))
    return review, decision, completed


class ApiService:
    def __init__(self, error=None) -> None:
        self.review, self.decision, self.completed = records()
        self.error = error
        self.calls = []

    def _result(self, value):
        if self.error is not None:
            raise self.error
        return value

    def create_review(self, **kwargs):
        self.calls.append(("create", kwargs))
        return self._result(self.review)

    def get_review(self, **kwargs):
        self.calls.append(("get", kwargs))
        return self._result(self.review)

    def list_decisions(self, **kwargs):
        self.calls.append(("list", kwargs))
        return self._result(ReviewDecisionPage((self.decision,), "next-page"))

    def submit_decision(self, **kwargs):
        self.calls.append(("decision", kwargs))
        return self._result(self.decision)

    def complete_review(self, **kwargs):
        self.calls.append(("complete", kwargs))
        return self._result(self.completed)


def override(service: ApiService) -> None:
    app.dependency_overrides[get_product_review_service] = lambda: service


def test_review_endpoints_return_camel_case_contracts_and_request_ids(client: TestClient) -> None:
    service = ApiService()
    override(service)
    product_id, review_id = service.review.product_id, service.review.review_id
    response = client.post(
        f"/api/v1/products/{product_id}/reviews",
        json={"selectionId": str(service.review.selection_id)},
    )
    assert response.status_code == 201
    assert response.json()["reviewId"] == str(review_id)
    assert response.json()["completionReady"] is False
    assert response.headers["X-Request-ID"]

    response = client.get(f"/api/v1/products/{product_id}/reviews/{review_id}")
    assert response.status_code == 200 and response.json()["status"] == "OPEN"

    response = client.get(f"/api/v1/products/{product_id}/reviews/{review_id}/decisions?limit=10")
    assert response.status_code == 200
    assert response.json()["items"][0]["decisionType"] == "MANUAL_OVERRIDE"
    assert response.json()["nextCursor"] == "next-page"

    response = client.post(
        f"/api/v1/products/{product_id}/reviews/{review_id}/attributes/voltage/decisions",
        json={
            "version": 1,
            "decisionType": "MANUAL_OVERRIDE",
            "manualValue": "430",
            "manualUnit": "V",
            "reviewerId": "reviewer-local-001",
        },
    )
    assert response.status_code == 201
    assert response.json()["manualRawValue"] == "430"

    response = client.post(
        f"/api/v1/products/{product_id}/reviews/{review_id}/complete",
        json={"version": 2, "reviewerId": "reviewer-local-001"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"


@pytest.mark.parametrize(
    "payload",
    [
        {
            "version": 1,
            "decisionType": "APPROVE_CANDIDATE",
            "candidateId": "candidate-1",
            "reviewerId": "reviewer-local-001",
        },
        {
            "version": 1,
            "decisionType": "APPROVE_PROPOSED",
            "reviewerId": "reviewer-local-001",
        },
        {
            "version": 1,
            "decisionType": "REJECT_ALL",
            "reviewerId": "reviewer-local-001",
        },
    ],
)
def test_each_non_manual_decision_contract_reaches_service(
    client: TestClient, payload: dict[str, object]
) -> None:
    service = ApiService()
    override(service)
    response = client.post(
        f"/api/v1/products/{service.review.product_id}/reviews/{service.review.review_id}"
        "/attributes/voltage/decisions",
        json=payload,
    )
    assert response.status_code == 201
    assert service.calls[-1][0] == "decision"


@pytest.mark.parametrize(
    "payload",
    [
        {"decisionType": "REJECT_ALL", "reviewerId": "reviewer"},
        {"version": 0, "decisionType": "REJECT_ALL", "reviewerId": "reviewer"},
        {"version": 1, "decisionType": "REJECT_ALL", "reviewerId": ""},
        {"version": 1, "decisionType": "UNKNOWN", "reviewerId": "reviewer"},
        {"version": 1, "decisionType": "APPROVE_CANDIDATE", "reviewerId": "reviewer"},
        {
            "version": 1,
            "decisionType": "APPROVE_PROPOSED",
            "candidateId": "not-allowed",
            "reviewerId": "reviewer",
        },
        {"version": 1, "decisionType": "MANUAL_OVERRIDE", "reviewerId": "reviewer"},
        {
            "version": 1,
            "decisionType": "REJECT_ALL",
            "reviewerId": "reviewer",
            "comment": "x" * 2_001,
        },
        {
            "version": 1,
            "decisionType": "MANUAL_OVERRIDE",
            "manualValue": "x" * 10_001,
            "reviewerId": "reviewer",
        },
    ],
)
def test_decision_request_validation_returns_standard_422(
    client: TestClient, payload: dict[str, object]
) -> None:
    service = ApiService()
    override(service)
    response = client.post(
        f"/api/v1/products/{service.review.product_id}/reviews/{service.review.review_id}"
        "/attributes/voltage/decisions",
        json=payload,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"
    assert response.json()["requestId"] == response.headers["X-Request-ID"]


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (ProductReviewNotFoundError(), 404, "REVIEW_NOT_FOUND"),
        (ProductReviewVersionConflictError(), 409, "REVIEW_VERSION_CONFLICT"),
        (ProductReviewManualOverrideInvalidError(), 422, "REVIEW_MANUAL_OVERRIDE_INVALID"),
        (ProductReviewRepositoryError("secret-table"), 503, "REVIEW_STORAGE_UNAVAILABLE"),
    ],
)
def test_review_errors_use_safe_standard_envelope(
    client: TestClient, error: Exception, status: int, code: str
) -> None:
    service = ApiService(error)
    override(service)
    response = client.get(
        f"/api/v1/products/{service.review.product_id}/reviews/{service.review.review_id}"
    )
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.json()["requestId"] == response.headers["X-Request-ID"]
    assert "secret-table" not in response.text
