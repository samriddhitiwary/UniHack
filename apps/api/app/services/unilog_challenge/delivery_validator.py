"""Exact-schema and per-field delivery validation."""

from app.domain.unilog_challenge import UnilogDeliveryRecord
from app.domain.unilog_challenge.delivery_schema import UNILOG_DELIVERY_HEADERS


class UnilogDeliveryValidator:
    def validate(self, record: UnilogDeliveryRecord) -> tuple[str, ...]:
        values = record.as_dict()
        issues: list[str] = []
        if tuple(values) != UNILOG_DELIVERY_HEADERS or len(values) != 252:
            issues.append("INVALID_DELIVERY_SCHEMA")
        invoice = values["INVOICE_DESC"]
        if isinstance(invoice, str) and (len(invoice) > 40 or invoice != invoice.upper()):
            issues.append("INVALID_INVOICE_DESC")
        for index in range(1, 51):
            label = values[f"ATTRIBUTE_LABEL {index}"]
            value = values[f"ATTRIBUTE_VALUE {index}"]
            if label not in (None, "") and value in (None, ""):
                issues.append(f"INVALID_ATTRIBUTE_TRIPLE_{index}")
        if any(value in ("None", "null", "N/A", "UNKNOWN") for value in values.values()):
            issues.append("INVALID_BLANK_SENTINEL")
        return tuple(issues)
