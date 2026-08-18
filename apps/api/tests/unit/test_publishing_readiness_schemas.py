"""SPEC-032 request and response serialization tests."""

from app.schemas.catalog_projection import CatalogProjectionResponse
from app.schemas.publishing_readiness import (
    ApplyPublishingReadinessRequest,
    CatalogPublishingReadinessResponse,
)
from app.services.publishing_readiness_state import evaluate_publishing_readiness_state
from tests.fixtures.catalog_projection import projected_result


def test_apply_request_requires_uuid_and_strict_positive_integer() -> None:
    _, _, projection = projected_result()
    request = ApplyPublishingReadinessRequest(projectionId=projection.projection_id, version=3)
    assert request.projection_id == projection.projection_id
    assert request.model_dump(by_alias=True)["projectionId"] == projection.projection_id


def test_catalog_projection_response_is_camel_case_and_contains_compact_lineage() -> None:
    _, _, projection = projected_result()
    body = CatalogProjectionResponse.model_validate(projection).model_dump(
        by_alias=True, mode="json"
    )
    assert body["projectionId"] == str(projection.projection_id)
    assert body["schemaFingerprint"] == projection.schema_fingerprint
    assert body["attributes"][0]["reviewDecisionId"]
    assert "rawEvidence" not in str(body)


def test_readiness_response_serializes_booleans_versions_and_enums() -> None:
    product, _, projection = projected_result(manufacturer=None)
    state = evaluate_publishing_readiness_state(product=product, projection=projection)
    body = CatalogPublishingReadinessResponse.model_validate(state).model_dump(
        by_alias=True, mode="json"
    )
    assert body["projectionCurrent"] is True
    assert body["eligibleForReadyToPublish"] is True
    assert body["currentProductVersion"] == 3
    assert body["warningReasonCodes"] == ["MANUFACTURER_MISSING"]
