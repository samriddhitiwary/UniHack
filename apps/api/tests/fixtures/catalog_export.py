"""Deterministic catalog export fixtures."""

from dataclasses import replace
from uuid import UUID

from app.domain.catalog_export import CatalogExportResult, CatalogExportStatus
from app.domain.processing_jobs import ProcessingJob, ProcessingJobType
from app.services.catalog_csv_exporter import CatalogCsvExporter
from app.services.catalog_export_package_builder import CatalogExportPackageBuilder
from app.services.catalog_json_exporter import CatalogJsonExporter
from app.services.catalog_manifest_builder import CatalogManifestBuilder
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.catalog_projection import projected_result

EXPORT_ID = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
EXPORT_JOB_ID = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")


def package_builder(
    *, json_limit=2_000_000, csv_limit=2_000_000, manifest_limit=200_000, attributes=100
):
    return CatalogExportPackageBuilder(
        json_exporter=CatalogJsonExporter(),
        csv_exporter=CatalogCsvExporter(),
        manifest_builder=CatalogManifestBuilder(),
        max_json_bytes=json_limit,
        max_csv_bytes=csv_limit,
        max_manifest_bytes=manifest_limit,
        max_attributes=attributes,
    )


def export_job(projection, **changes):
    job = ProcessingJob.create(
        product_id=projection.product_id,
        source_id=None,
        job_type=ProcessingJobType.CATALOG_EXPORT,
        projection_id=projection.projection_id,
        now=NOW,
    )
    return replace(job, job_id=EXPORT_JOB_ID, **changes)


def export_result(*, manual=False, warning=False, **product_changes):
    product, _, projection = projected_result(manual=manual, warning=warning, **product_changes)
    package = package_builder().build(export_id=EXPORT_ID, projection=projection, created_at=NOW)
    result = CatalogExportResult(
        export_id=EXPORT_ID,
        job_id=EXPORT_JOB_ID,
        product_id=projection.product_id,
        projection_id=projection.projection_id,
        projection_product_version=projection.product_version,
        category=projection.category,
        schema_version=projection.schema_version,
        schema_fingerprint=projection.schema_fingerprint,
        projection_status=projection.status,
        status=CatalogExportStatus.EXPORTED,
        artifacts=package.artifacts,
        warning_reason_codes=projection.warning_reason_codes,
        engine="deterministic-catalog-exporter-v1",
        engine_version="1.0",
        created_at=NOW,
    )
    return product, projection, package, result
