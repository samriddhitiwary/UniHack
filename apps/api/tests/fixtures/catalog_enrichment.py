"""Grounded catalog enrichment fixtures."""

import json
from dataclasses import replace
from uuid import UUID

from app.domain.catalog_enrichment import CatalogEnrichmentResult
from app.domain.processing_jobs import ProcessingJob, ProcessingJobType
from app.services.catalog_enrichment_trusted_facts import CatalogEnrichmentTrustedFactBuilder
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.catalog_projection import projected_result

ENRICHMENT_ID = UUID("aeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
ENRICHMENT_JOB_ID = UUID("addddddd-dddd-4ddd-8ddd-dddddddddddd")


def enrichment_projection(*, manual=False, warning=False, **changes):
    product, materialization, projection = projected_result(manual=manual, warning=warning)
    return product, materialization, replace(projection, **changes)


def enrichment_job(projection, **changes):
    job = ProcessingJob.create(
        product_id=projection.product_id,
        source_id=None,
        job_type=ProcessingJobType.AI_CATALOG_ENRICHMENT,
        projection_id=projection.projection_id,
        now=NOW,
    )
    return replace(job, job_id=ENRICHMENT_JOB_ID, **changes)


def trusted_facts(projection):
    return CatalogEnrichmentTrustedFactBuilder(max_facts=200, max_value_characters=10_000).build(
        projection
    )


def grounded_payload(projection, **changes):
    facts = trusted_facts(projection)
    attributes = [fact for fact in facts.facts if fact.fact_id.startswith("ATTRIBUTE:")]
    while len(attributes) < 3:
        attributes.append(facts.facts[len(attributes)])
    payload = {
        "title": {
            "text": projection.product_name,
            "factIds": ["IDENTITY:name"],
        },
        "description": {
            "text": f"{projection.product_name} {projection.category.value}",
            "factIds": ["IDENTITY:name", "IDENTITY:category"],
        },
        "featureBullets": [
            {
                "text": " ".join(part for part in (fact.value, fact.unit) if part),
                "factIds": [fact.fact_id],
            }
            for fact in attributes[:3]
        ],
        "searchKeywords": [{"text": projection.category.value, "factIds": ["IDENTITY:category"]}],
        "technicalSummary": {
            "text": " | ".join(
                " ".join(part for part in (fact.value, fact.unit) if part)
                for fact in attributes[:3]
            ),
            "factIds": [fact.fact_id for fact in attributes[:3]],
        },
    }
    payload.update(changes)
    return payload


def grounded_response(projection, **changes) -> str:
    return json.dumps(grounded_payload(projection, **changes), separators=(",", ":"))


class FakeLlm:
    provider = "fake"
    model = "grounded-test-model"

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str]] = []

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.responses.pop(0)


def copy_result(result: CatalogEnrichmentResult, **changes) -> CatalogEnrichmentResult:
    return replace(result, **changes)
