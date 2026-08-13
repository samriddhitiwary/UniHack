from uuid import uuid4

from app.domain.category_schemas.builtins import induction_motor_schema_v1
from app.schemas.attribute_normalization import AttributeNormalizationResultRecord
from app.services.attribute_normalization_engine import AttributeNormalizationEngine
from tests.fixtures.attribute_normalization import NOW, candidate, extraction


def test_internal_normalization_schema_serializes_camel_case_lineage() -> None:
    schema = induction_motor_schema_v1()
    result = AttributeNormalizationEngine().normalize(
        job_id=uuid4(),
        extraction_result=extraction(schema, (candidate(schema, "ratedPower", "5500", "W"),)),
        schema=schema,
        now=NOW,
    )
    payload = AttributeNormalizationResultRecord.model_validate(result).model_dump(
        mode="json", by_alias=True
    )
    assert payload["extractionId"] == str(result.extraction_id)
    assert payload["candidates"][0]["normalizedValue"] == "5.5"
    assert payload["candidates"][0]["conversionApplied"] is True
