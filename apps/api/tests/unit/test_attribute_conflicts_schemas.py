from app.schemas.attribute_conflicts import AttributeConflictDetectionResultRecord
from tests.unit.test_attribute_conflicts_repository import result_fixture


def test_result_schema_serializes_domain_with_camel_case_aliases() -> None:
    payload = AttributeConflictDetectionResultRecord.model_validate(result_fixture()).model_dump(
        mode="json", by_alias=True
    )
    assert payload["conflictDetectionId"]
    assert payload["attributes"][0]["candidateIds"]
    assert "selectedValue" not in payload["attributes"][0]
