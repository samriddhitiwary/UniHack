import pytest
from pydantic import ValidationError

from app.schemas.catalog_projection import CommerceCatalogProjectionRecord
from tests.fixtures.catalog_projection import projected_result


def test_internal_schema_round_trip_includes_lineage_nulls_and_camel_case() -> None:
    result = projected_result(manual=True, clean=False)[2]
    record = CommerceCatalogProjectionRecord.model_validate(result)
    payload = record.model_dump()
    assert payload["projectionId"] == result.projection_id
    assert payload["productVersion"] == 3
    assert payload["attributes"][0]["reviewDecisionId"]
    assert isinstance(payload["warningReasonCodes"], tuple)
    with pytest.raises(ValidationError):
        CommerceCatalogProjectionRecord.model_validate({**payload, "unexpected": True})
