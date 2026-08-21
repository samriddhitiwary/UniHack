"""Grounded description construction and optional model-boundary tests."""

import json

from app.services.unilog_challenge.description_builder import UnilogDescriptionBuilder
from app.services.unilog_challenge.model_assistance import UnilogModelSignalAssistant
from tests.unit.unilog_challenge.helpers import challenge_row


def test_all_description_builders_are_grounded_and_invoice_is_bounded_uppercase() -> None:
    facts = {
        "mpn": "DCB518ASTS06G",
        "brand": "Diablo",
        "product_type": "Sanding Belt",
        "dimensions": "1/2 x 18 in",
        "quantity": "6 pc",
        "grit": "P150",
    }
    results = UnilogDescriptionBuilder().build_all(
        facts,
        raw_evidence='DCB518ASTS06G Diablo 1/2"x18" Sanding Belt 6pc P150',
    )
    by_field = {item.field_name: item for item in results}
    assert set(by_field) == {
        "Product Name",
        "INVOICE_DESC",
        "MOBILE_DESC",
        "SHORT_DESC",
        "LONG_DESC1",
        "RETAIL_DESC",
        "MARKETING_DESCRIPTION",
    }
    invoice = by_field["INVOICE_DESC"].value
    assert invoice is not None and invoice == invoice.upper() and len(invoice) <= 40
    assert by_field["Product Name"].value == "Sanding Belt"
    assert all(item.fact_ids and item.field_provenance for item in results)
    assert all("premium" not in (item.value or "").casefold() for item in results)


def test_mobile_description_warns_instead_of_fabricating_padding() -> None:
    results = UnilogDescriptionBuilder().build_all(
        {"mpn": "ABC", "product_type": "Valve"}, raw_evidence="ABC Valve"
    )
    mobile = next(item for item in results if item.field_name == "MOBILE_DESC")
    assert mobile.value == "Valve, ABC"
    assert mobile.validation_issues == ("FORMAT_WARNING_MOBILE_LENGTH",)


def test_description_builder_blanks_fatal_unsupported_numeric_or_marketing_claim() -> None:
    builder = UnilogDescriptionBuilder()
    numeric = builder._result(
        "SHORT_DESC", "Valve 240", {"product_type": "Valve"}, raw_evidence="Valve"
    )
    assert numeric.value is None
    assert "INVALID_UNSUPPORTED_NUMBER" in numeric.validation_issues
    claim = builder._result(
        "MARKETING_DESCRIPTION",
        "Premium Valve",
        {"product_type": "Valve"},
        raw_evidence="Valve",
    )
    assert claim.value is None


def test_descriptions_remain_blank_when_product_type_is_unknown() -> None:
    results = UnilogDescriptionBuilder().build_all({"mpn": "ABC"}, raw_evidence="ABC Thing")
    assert len(results) == 7
    assert all(item.value is None and item.fact_ids == () for item in results)


class _FakeProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.payloads: list[dict[str, object]] = []

    def complete_json(self, payload: dict[str, object]) -> str:
        self.payloads.append(payload)
        return self.responses.pop(0)


def test_model_assistance_accepts_only_exact_grounded_spans_and_no_expected_answer() -> None:
    provider = _FakeProvider(
        [
            json.dumps(
                {"productType": "Sanding Belt", "attributes": [{"name": "Grit", "value": "P150"}]}
            )
        ]
    )
    result = UnilogModelSignalAssistant(provider).propose(challenge_row())
    assert result is not None
    assert result.product_type == "Sanding Belt"
    assert result.attributes == (("Grit", "P150"),)
    serialized = json.dumps(provider.payloads[0])
    assert "expected" not in serialized.casefold()
    assert "delivery" not in serialized.casefold()


def test_model_assistance_has_two_attempt_limit_and_deterministic_failure() -> None:
    provider = _FakeProvider(["not-json", '{"productType":"invented","attributes":[]}'])
    assert UnilogModelSignalAssistant(provider).propose(challenge_row()) is None
    assert len(provider.payloads) == 2
    assert provider.payloads[1]["repair"] == "Return valid JSON using only exact source spans."
