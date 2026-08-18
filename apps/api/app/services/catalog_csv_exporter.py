"""Deterministic one-product flat CSV serialization."""

import csv
import io

from app.core.exceptions import CatalogExportSerializationError
from app.domain.catalog_projection import CommerceCatalogProjection

FIXED_COLUMNS = (
    "productId",
    "productVersion",
    "productName",
    "manufacturer",
    "modelNumber",
    "category",
    "description",
    "projectionId",
    "projectionStatus",
    "schemaVersion",
    "schemaFingerprint",
    "warningReasonCodes",
)


class CatalogCsvExporter:
    def serialize(self, *, projection: CommerceCatalogProjection) -> bytes:
        try:
            headers = list(FIXED_COLUMNS)
            values: list[object] = [
                str(projection.product_id),
                str(projection.product_version),
                projection.product_name,
                projection.manufacturer or "",
                projection.model_number or "",
                projection.category.value,
                projection.description or "",
                str(projection.projection_id),
                projection.status.value,
                str(projection.schema_version),
                projection.schema_fingerprint,
                "|".join(reason.value for reason in projection.warning_reason_codes),
            ]
            for attribute in projection.attributes:
                headers.append(attribute.attribute_name)
                values.append(attribute.value)
                if attribute.unit is not None:
                    headers.append(f"{attribute.attribute_name}Unit")
                    values.append(attribute.unit)
            output = io.StringIO(newline="")
            writer = csv.writer(output, lineterminator="\n")
            writer.writerow(headers)
            writer.writerow(values)
            return output.getvalue().encode("utf-8")
        except (csv.Error, TypeError, ValueError, UnicodeError) as exc:
            raise CatalogExportSerializationError() from exc
