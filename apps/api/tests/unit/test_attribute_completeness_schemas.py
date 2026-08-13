from uuid import uuid4

from app.schemas.attribute_completeness import AttributeCompletenessResultRecord
from app.services.attribute_completeness_engine import AttributeCompletenessEngine
from tests.fixtures.attribute_normalization import NOW
from tests.unit.test_attribute_completeness_engine import conflict_for


def test_completeness_schema_serializes_camel_case_without_selected_values() -> None:
    schema, conflict = conflict_for(("voltage", "415", "V"))
    result = AttributeCompletenessEngine().evaluate(
        job_id=uuid4(), conflict_result=conflict, schema=schema, now=NOW
    )
    payload = AttributeCompletenessResultRecord.model_validate(result).model_dump(
        mode="json", by_alias=True
    )
    assert payload["requiredResolvedBp"] == result.required_resolved_bp
    assert next(item for item in payload["attributes"] if item["attributeName"] == "voltage")[
        "candidateIds"
    ]
    assert "selectedValue" not in payload["attributes"][0]
