"""Canonical catalog JSON serializer tests."""

import json
from dataclasses import replace

from app.services.catalog_json_exporter import CatalogJsonExporter
from tests.fixtures.catalog_export import export_result


def test_canonical_json_is_byte_deterministic_compact_utf8_with_newline() -> None:
    _, projection, _, _ = export_result()
    exporter = CatalogJsonExporter()
    first = exporter.serialize(projection=projection)
    assert first == exporter.serialize(projection=projection)
    assert first.endswith(b"\n") and not first.startswith(b"\xef\xbb\xbf")
    assert b"\n" not in first[:-1]


def test_canonical_json_contains_schema_identity_attributes_warnings_and_lineage() -> None:
    _, projection, _, _ = export_result(manufacturer=None)
    body = json.loads(CatalogJsonExporter().serialize(projection=projection))
    assert body["schema"] == {"name": "catalogiq-commerce-catalog", "version": 1}
    assert body["product"]["productId"] == str(projection.product_id)
    assert body["product"]["productVersion"] == 3
    assert body["catalog"]["warningReasonCodes"] == ["MANUFACTURER_MISSING"]
    assert body["catalog"]["attributes"][0]["value"] == projection.attributes[0].value
    assert body["lineage"]["materializationId"] == str(projection.materialization_id)
    assert "rawEvidence" not in str(body)


def test_json_special_characters_round_trip_without_ascii_escaping() -> None:
    _, projection, _, _ = export_result()
    special = replace(
        projection,
        product_name='Motor / "Prüfung"',
        description="Line one\nLine two Ω",
    )
    encoded = CatalogJsonExporter().serialize(projection=special)
    body = json.loads(encoded)
    assert body["product"]["name"] == 'Motor / "Prüfung"'
    assert body["product"]["description"] == "Line one\nLine two Ω"
    assert "Ω" in encoded.decode("utf-8")


def test_human_override_and_validation_warning_are_preserved_without_comment() -> None:
    _, projection, _, _ = export_result(manual=True, warning=True)
    body = json.loads(CatalogJsonExporter().serialize(projection=projection))
    origins = {item["origin"] for item in body["catalog"]["attributes"]}
    statuses = {item["validationStatus"] for item in body["catalog"]["attributes"]}
    assert "HUMAN_OVERRIDE" in origins
    assert "VALID_WITH_WARNINGS" in statuses
    assert "comment" not in str(body).lower()
