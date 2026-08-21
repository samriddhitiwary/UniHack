"""Assemble validated field resolutions into the immutable 252-column contract."""

from collections.abc import Iterable

from app.domain.unilog_challenge import (
    FieldValidationStatus,
    UnilogDeliveryRecord,
    UnilogFieldResolution,
)
from app.domain.unilog_challenge.delivery_schema import UNILOG_DELIVERY_HEADERS
from app.services.unilog_challenge.delivery_validator import UnilogDeliveryValidator
from app.services.unilog_challenge.policy import require_supported_provenance


class UnilogDeliveryRecordAssembler:
    def __init__(self, validator: UnilogDeliveryValidator | None = None) -> None:
        self._validator = validator or UnilogDeliveryValidator()

    def assemble(self, resolutions: Iterable[UnilogFieldResolution]) -> UnilogDeliveryRecord:
        values: dict[str, str | None] = {header: None for header in UNILOG_DELIVERY_HEADERS}
        seen: set[str] = set()
        for item in resolutions:
            if item.field_name in seen:
                raise ValueError(f"duplicate field resolution: {item.field_name}")
            seen.add(item.field_name)
            if item.field_name not in values:
                raise ValueError(f"field is outside delivery schema: {item.field_name}")
            if item.value is None or item.validation_status is FieldValidationStatus.INVALID:
                continue
            if item.provenance is None:
                raise ValueError("populated resolution has no provenance")
            require_supported_provenance(item.provenance)
            values[item.field_name] = item.value
        record = UnilogDeliveryRecord.from_mapping(values)
        issues = self._validator.validate(record)
        if issues:
            raise ValueError(f"delivery record validation failed: {','.join(issues)}")
        return record
