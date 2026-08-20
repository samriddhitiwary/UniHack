"""Composition root for existing services used by the catalog workflow."""

from uuid import UUID

from botocore.client import BaseClient

from app.core.config import Settings
from app.domain.processing_jobs import ProcessingJobType
from app.repositories.catalog_projection import CommerceCatalogProjectionRepository
from app.repositories.dynamodb_attribute_completeness import (
    DynamoDBAttributeCompletenessResultRepository,
)
from app.repositories.dynamodb_attribute_conflicts import (
    DynamoDBAttributeConflictDetectionResultRepository,
)
from app.repositories.dynamodb_attribute_normalization import (
    DynamoDBAttributeNormalizationResultRepository,
)
from app.repositories.dynamodb_attribute_selection import DynamoDBAttributeSelectionResultRepository
from app.repositories.dynamodb_attribute_validation import (
    DynamoDBAttributeValidationResultRepository,
)
from app.repositories.dynamodb_catalog_enrichment import DynamoDBCatalogEnrichmentResultRepository
from app.repositories.dynamodb_catalog_export import DynamoDBCatalogExportResultRepository
from app.repositories.dynamodb_category_schemas import DynamoDBCategoryAttributeSchemaRepository
from app.repositories.dynamodb_csv_processing import DynamoDBCsvProcessingResultRepository
from app.repositories.dynamodb_image_analysis import DynamoDBImageAnalysisResultRepository
from app.repositories.dynamodb_image_ocr import DynamoDBImageOcrResultRepository
from app.repositories.dynamodb_pdf_extraction import DynamoDBPdfExtractionResultRepository
from app.repositories.dynamodb_pdf_table_extraction import DynamoDBPdfTableExtractionRepository
from app.repositories.dynamodb_product_classification import (
    DynamoDBProductClassificationResultRepository,
)
from app.repositories.dynamodb_product_intelligence import (
    DynamoDBProductIntelligenceScoreRepository,
)
from app.repositories.dynamodb_reviewed_attributes import (
    DynamoDBFinalReviewedAttributeRepository,
)
from app.repositories.dynamodb_structured_attribute_extraction import (
    DynamoDBStructuredAttributeExtractionResultRepository,
)
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_review import ProductReviewRepository
from app.repositories.product_sources import ProductSourceRepository
from app.repositories.products import ProductRepository
from app.services.attribute_completeness import AttributeCompletenessService
from app.services.attribute_completeness_engine import AttributeCompletenessEngine
from app.services.attribute_conflict_detection import AttributeConflictDetectionService
from app.services.attribute_conflict_detection_engine import AttributeConflictDetectionEngine
from app.services.attribute_normalization import AttributeNormalizationService
from app.services.attribute_normalization_engine import AttributeNormalizationEngine
from app.services.attribute_selection import AttributeSelectionService
from app.services.attribute_selection_engine import AttributeSelectionEngine
from app.services.attribute_validation import AttributeValidationService
from app.services.attribute_validation_engine import AttributeValidationEngine
from app.services.catalog_csv_exporter import CatalogCsvExporter
from app.services.catalog_enrichment import CatalogEnrichmentService
from app.services.catalog_enrichment_engine import CatalogEnrichmentEngine
from app.services.catalog_enrichment_grounding_validator import (
    CatalogEnrichmentGroundingValidator,
)
from app.services.catalog_enrichment_hallucination_guard import CatalogEnrichmentHallucinationGuard
from app.services.catalog_enrichment_llm import OpenAICatalogEnrichmentLlm
from app.services.catalog_enrichment_prompt_builder import CatalogEnrichmentPromptBuilder
from app.services.catalog_enrichment_response_parser import CatalogEnrichmentResponseParser
from app.services.catalog_enrichment_trusted_facts import CatalogEnrichmentTrustedFactBuilder
from app.services.catalog_export import CatalogExportService
from app.services.catalog_export_package_builder import CatalogExportPackageBuilder
from app.services.catalog_json_exporter import CatalogJsonExporter
from app.services.catalog_manifest_builder import CatalogManifestBuilder
from app.services.catalog_product_identity_projector import CatalogProductIdentityProjector
from app.services.catalog_projection import CatalogProjectionService
from app.services.catalog_projection_engine import CatalogProjectionEngine
from app.services.catalog_publishing_readiness import CatalogPublishingReadinessEvaluator
from app.services.catalog_reviewed_attribute_projector import CatalogReviewedAttributeProjector
from app.services.catalog_workflow_stage_executor import (
    ExistingServicesCatalogWorkflowStageExecutor,
)
from app.services.csv_parser import CsvParser, CsvProcessingLimits
from app.services.csv_processing import CsvProcessingService
from app.services.image_analysis import ImageAnalysisService
from app.services.image_inspector import ImageAnalysisLimits, ImageInspector
from app.services.image_ocr import ImageOcrService
from app.services.image_ocr_pipeline import ImageOcrLimits
from app.services.ocr_engine import RapidOcrEngine
from app.services.pdf_table_extraction import PdfTableExtractionService
from app.services.pdf_table_parser import PdfTableExtractionLimits, PdfTableParser
from app.services.pdf_text_extraction import PdfTextExtractionService
from app.services.pdf_text_parser import PdfExtractionLimits, PdfTextParser
from app.services.product_classification import ProductClassificationService
from app.services.product_classification_engine import ProductClassificationEngine
from app.services.product_classification_evidence import ProductClassificationEvidenceAggregator
from app.services.product_intelligence_engine import ProductIntelligenceEngine
from app.services.product_intelligence_score import ProductIntelligenceScoreService
from app.services.product_review import ProductReviewService
from app.services.publishing_readiness_application import PublishingReadinessApplicationService
from app.services.review_decision_resolver import ReviewDecisionResolver
from app.services.reviewed_attribute_materialization import ReviewedAttributeMaterializationService
from app.services.reviewed_attribute_materialization_engine import (
    ReviewedAttributeMaterializationEngine,
)
from app.services.structured_attribute_evidence import StructuredAttributeEvidenceAggregator
from app.services.structured_attribute_extraction import StructuredAttributeExtractionService
from app.services.structured_attribute_extraction_engine import (
    StructuredAttributeExtractionEngine,
)
from app.storage.protocol import ObjectStorage


def build_catalog_workflow_stage_executor(
    *,
    client: BaseClient,
    settings: Settings,
    jobs: ProcessingJobRepository,
    products: ProductRepository,
    sources: ProductSourceRepository,
    reviews: ProductReviewRepository,
    projections: CommerceCatalogProjectionRepository,
    review_service: ProductReviewService,
    storage: ObjectStorage,
) -> ExistingServicesCatalogWorkflowStageExecutor:
    """Build adapters once per request; expensive OCR/LLM providers remain lazy."""
    pdf_text = DynamoDBPdfExtractionResultRepository(
        client, settings.table_name("pdf-extraction-results")
    )
    pdf_tables = DynamoDBPdfTableExtractionRepository(
        client, settings.table_name("pdf-table-extraction-results")
    )
    csv_results = DynamoDBCsvProcessingResultRepository(
        client, settings.table_name("csv-processing-results")
    )
    image_analysis = DynamoDBImageAnalysisResultRepository(
        client, settings.table_name("image-analysis-results")
    )
    image_ocr = DynamoDBImageOcrResultRepository(client, settings.table_name("image-ocr-results"))
    classifications = DynamoDBProductClassificationResultRepository(
        client, settings.table_name("product-classification-results")
    )
    schemas = DynamoDBCategoryAttributeSchemaRepository(
        client, settings.table_name("category-attribute-schemas")
    )
    extractions = DynamoDBStructuredAttributeExtractionResultRepository(
        client, settings.table_name("structured-attribute-extraction-results")
    )
    normalizations = DynamoDBAttributeNormalizationResultRepository(
        client, settings.table_name("attribute-normalization-results")
    )
    conflicts = DynamoDBAttributeConflictDetectionResultRepository(
        client, settings.table_name("attribute-conflict-detection-results")
    )
    completeness = DynamoDBAttributeCompletenessResultRepository(
        client, settings.table_name("attribute-completeness-results")
    )
    validations = DynamoDBAttributeValidationResultRepository(
        client, settings.table_name("attribute-validation-results")
    )
    selections = DynamoDBAttributeSelectionResultRepository(
        client, settings.table_name("attribute-selection-results")
    )
    materializations = DynamoDBFinalReviewedAttributeRepository(
        client, settings.table_name("reviewed-attribute-results")
    )
    exports = DynamoDBCatalogExportResultRepository(
        client, settings.table_name("catalog-export-results")
    )
    enrichments = DynamoDBCatalogEnrichmentResultRepository(
        client, settings.table_name("catalog-enrichment-results")
    )
    scores = DynamoDBProductIntelligenceScoreRepository(
        client, settings.table_name("product-intelligence-score-results")
    )

    pdf_text_service = PdfTextExtractionService(
        jobs,
        sources,
        storage,
        pdf_text,
        PdfTextParser(
            PdfExtractionLimits(
                max_pages=settings.pdf_extraction_max_pages,
                max_total_characters=settings.pdf_extraction_max_total_characters,
                max_page_characters=settings.pdf_extraction_max_page_characters,
            )
        ),
    )
    pdf_table_service = PdfTableExtractionService(
        jobs,
        sources,
        storage,
        pdf_tables,
        PdfTableParser(
            PdfTableExtractionLimits(
                max_pages=settings.pdf_table_extraction_max_pages,
                max_tables=settings.pdf_table_extraction_max_tables,
                max_rows_per_table=settings.pdf_table_extraction_max_rows_per_table,
                max_columns_per_table=settings.pdf_table_extraction_max_columns_per_table,
                max_cells=settings.pdf_table_extraction_max_cells,
                max_cell_characters=settings.pdf_table_extraction_max_cell_characters,
            )
        ),
    )
    csv_service = CsvProcessingService(
        jobs,
        sources,
        storage,
        csv_results,
        CsvParser(
            CsvProcessingLimits(
                max_file_bytes=settings.csv_processing_max_file_bytes,
                max_rows=settings.csv_processing_max_rows,
                max_columns=settings.csv_processing_max_columns,
                max_total_cells=settings.csv_processing_max_total_cells,
                max_cell_characters=settings.csv_processing_max_cell_characters,
                sample_bytes=settings.csv_processing_sample_bytes,
            )
        ),
    )
    image_analysis_service = ImageAnalysisService(
        jobs,
        sources,
        storage,
        image_analysis,
        ImageInspector(
            ImageAnalysisLimits(
                max_file_bytes=settings.image_analysis_max_file_bytes,
                max_width=settings.image_analysis_max_width,
                max_height=settings.image_analysis_max_height,
                max_pixels=settings.image_analysis_max_pixels,
                max_regions=settings.image_analysis_max_regions,
            )
        ),
    )

    classification_service = ProductClassificationService(
        job_repository=jobs,
        product_repository=products,
        result_repository=classifications,
        evidence_aggregator=ProductClassificationEvidenceAggregator(
            source_repository=sources,
            job_repository=jobs,
            pdf_text_repository=pdf_text,
            pdf_table_repository=pdf_tables,
            csv_repository=csv_results,
            image_ocr_repository=image_ocr,
            max_items=settings.product_classification_max_evidence_items,
            max_total_characters=settings.product_classification_max_total_characters,
            max_item_characters=settings.product_classification_max_item_characters,
        ),
        engine=ProductClassificationEngine(max_matches=settings.product_classification_max_matches),
    )
    extraction_service = StructuredAttributeExtractionService(
        job_repository=jobs,
        product_repository=products,
        classification_repository=classifications,
        schema_repository=schemas,
        result_repository=extractions,
        evidence_aggregator=StructuredAttributeEvidenceAggregator(
            source_repository=sources,
            job_repository=jobs,
            pdf_text_repository=pdf_text,
            pdf_table_repository=pdf_tables,
            csv_repository=csv_results,
            image_ocr_repository=image_ocr,
            max_items=settings.attribute_extraction_max_evidence_items,
            max_total_characters=settings.attribute_extraction_max_total_characters,
            max_item_characters=settings.attribute_extraction_max_item_characters,
        ),
        engine=StructuredAttributeExtractionEngine(
            max_candidates=settings.attribute_extraction_max_candidates,
            max_candidates_per_attribute=(
                settings.attribute_extraction_max_candidates_per_attribute
            ),
            max_excerpt_characters=settings.attribute_extraction_max_excerpt_characters,
        ),
    )
    normalization_service = AttributeNormalizationService(
        job_repository=jobs,
        product_repository=products,
        extraction_repository=extractions,
        schema_repository=schemas,
        result_repository=normalizations,
        engine=AttributeNormalizationEngine(
            max_decimal_places=settings.attribute_normalization_max_decimal_places,
            max_candidates=settings.attribute_normalization_max_candidates,
            max_normalized_value_characters=(
                settings.attribute_normalization_max_normalized_value_characters
            ),
        ),
    )
    conflict_service = AttributeConflictDetectionService(
        job_repository=jobs,
        product_repository=products,
        normalization_repository=normalizations,
        result_repository=conflicts,
        engine=AttributeConflictDetectionEngine(
            relative_tolerance_bp=settings.attribute_conflict_numeric_relative_tolerance_bp,
            absolute_tolerance=settings.attribute_conflict_numeric_absolute_tolerance,
            max_attributes=settings.attribute_conflict_max_attributes,
            max_candidates_per_attribute=(settings.attribute_conflict_max_candidates_per_attribute),
            max_groups_per_attribute=settings.attribute_conflict_max_groups_per_attribute,
        ),
    )
    completeness_service = AttributeCompletenessService(
        job_repository=jobs,
        product_repository=products,
        conflict_repository=conflicts,
        schema_repository=schemas,
        result_repository=completeness,
        engine=AttributeCompletenessEngine(
            max_attributes=settings.attribute_completeness_max_attributes,
            max_candidate_ids_per_attribute=(
                settings.attribute_completeness_max_candidate_ids_per_attribute
            ),
        ),
    )
    validation_service = AttributeValidationService(
        job_repository=jobs,
        product_repository=products,
        normalization_repository=normalizations,
        schema_repository=schemas,
        result_repository=validations,
        engine=AttributeValidationEngine(
            max_candidates=settings.attribute_validation_max_candidates,
            max_attributes=settings.attribute_validation_max_attributes,
            max_value_characters=settings.attribute_validation_max_value_characters,
            max_pattern_characters=settings.attribute_validation_max_pattern_characters,
            max_issues_per_candidate=settings.attribute_validation_max_issues_per_candidate,
            max_total_issues=settings.attribute_validation_max_total_issues,
        ),
    )
    selection_service = AttributeSelectionService(
        job_repository=jobs,
        product_repository=products,
        conflict_repository=conflicts,
        validation_repository=validations,
        completeness_repository=completeness,
        normalization_repository=normalizations,
        result_repository=selections,
        engine=AttributeSelectionEngine(
            auto_select_min_confidence_bp=(
                settings.attribute_selection_auto_select_min_confidence_bp
            ),
            min_distinct_sources=settings.attribute_selection_min_distinct_sources,
            max_attributes=settings.attribute_selection_max_attributes,
            max_candidate_ids_per_attribute=(
                settings.attribute_selection_max_candidate_ids_per_attribute
            ),
            max_reason_codes_per_attribute=(
                settings.attribute_selection_max_reason_codes_per_attribute
            ),
        ),
    )
    materialization_service = ReviewedAttributeMaterializationService(
        job_repository=jobs,
        product_repository=products,
        review_repository=reviews,
        selection_repository=selections,
        validation_repository=validations,
        normalization_repository=normalizations,
        schema_repository=schemas,
        result_repository=materializations,
        resolver=ReviewDecisionResolver(),
        engine=ReviewedAttributeMaterializationEngine(
            max_attributes=settings.reviewed_materialization_max_attributes,
            max_value_characters=settings.reviewed_materialization_max_value_characters,
            max_manual_raw_characters=(settings.reviewed_materialization_max_manual_raw_characters),
        ),
    )
    projection_service = CatalogProjectionService(
        job_repository=jobs,
        product_repository=products,
        materialization_repository=materializations,
        result_repository=projections,
        engine=CatalogProjectionEngine(
            identity_projector=CatalogProductIdentityProjector(
                max_text_characters=settings.catalog_projection_max_product_text_characters
            ),
            attribute_projector=CatalogReviewedAttributeProjector(
                max_attributes=settings.catalog_projection_max_attributes,
                max_value_characters=settings.catalog_projection_max_value_characters,
            ),
            readiness_evaluator=CatalogPublishingReadinessEvaluator(
                max_reason_codes=settings.catalog_projection_max_reason_codes
            ),
        ),
    )
    export_service = CatalogExportService(
        job_repository=jobs,
        product_repository=products,
        projection_repository=projections,
        result_repository=exports,
        object_storage=storage,
        package_builder=CatalogExportPackageBuilder(
            json_exporter=CatalogJsonExporter(),
            csv_exporter=CatalogCsvExporter(),
            manifest_builder=CatalogManifestBuilder(),
            max_json_bytes=settings.catalog_export_max_json_bytes,
            max_csv_bytes=settings.catalog_export_max_csv_bytes,
            max_manifest_bytes=settings.catalog_export_max_manifest_bytes,
            max_attributes=settings.catalog_export_max_attributes,
        ),
    )
    score_service = ProductIntelligenceScoreService(
        job_repository=jobs,
        product_repository=products,
        projection_repository=projections,
        completeness_repository=completeness,
        validation_repository=validations,
        conflict_repository=conflicts,
        selection_repository=selections,
        review_repository=reviews,
        materialization_repository=materializations,
        enrichment_repository=enrichments,
        result_repository=scores,
        engine=ProductIntelligenceEngine(),
        max_attributes=settings.catalog_projection_max_attributes,
    )

    def run_ocr(*, job_id: UUID) -> object:
        service = ImageOcrService(
            jobs,
            sources,
            image_analysis,
            image_ocr,
            storage,
            RapidOcrEngine(),
            ImageOcrLimits(
                max_regions=settings.image_ocr_max_regions,
                max_blocks=settings.image_ocr_max_blocks,
                max_total_characters=settings.image_ocr_max_total_characters,
                max_block_characters=settings.image_ocr_max_block_characters,
                minimum_confidence_bp=settings.image_ocr_min_confidence_bp,
            ),
        )
        return service.recognize_for_job(job_id=job_id)

    def run_enrichment(*, job_id: UUID) -> object:
        engine = CatalogEnrichmentEngine(
            llm=OpenAICatalogEnrichmentLlm(settings),
            fact_builder=CatalogEnrichmentTrustedFactBuilder(
                max_facts=settings.ai_enrichment_max_trusted_facts,
                max_value_characters=settings.ai_enrichment_max_fact_value_characters,
            ),
            prompt_builder=CatalogEnrichmentPromptBuilder(),
            parser=CatalogEnrichmentResponseParser(
                max_title=settings.ai_enrichment_max_title_characters,
                max_description=settings.ai_enrichment_max_description_characters,
                max_bullets=settings.ai_enrichment_max_feature_bullets,
                max_bullet=settings.ai_enrichment_max_bullet_characters,
                max_keywords=settings.ai_enrichment_max_search_keywords,
                max_keyword=settings.ai_enrichment_max_keyword_characters,
                max_summary=settings.ai_enrichment_max_technical_summary_characters,
                max_refs_per_item=settings.ai_enrichment_max_fact_references_per_item,
                max_total_refs=settings.ai_enrichment_max_total_fact_references,
            ),
            validator=CatalogEnrichmentGroundingValidator(CatalogEnrichmentHallucinationGuard()),
            max_attempts=settings.ai_enrichment_max_generation_attempts,
        )
        return CatalogEnrichmentService(
            job_repository=jobs,
            product_repository=products,
            projection_repository=projections,
            result_repository=enrichments,
            engine=engine,
        ).enrich_for_job(job_id=job_id)

    runners = {
        ProcessingJobType.PDF_TEXT_EXTRACTION: pdf_text_service.extract_for_job,
        ProcessingJobType.PDF_TABLE_EXTRACTION: pdf_table_service.extract_for_job,
        ProcessingJobType.CSV_PROCESSING: csv_service.process_for_job,
        ProcessingJobType.IMAGE_ANALYSIS: image_analysis_service.analyze_for_job,
        ProcessingJobType.IMAGE_OCR: run_ocr,
        ProcessingJobType.PRODUCT_CLASSIFICATION: classification_service.classify_for_job,
        ProcessingJobType.ATTRIBUTE_EXTRACTION: extraction_service.extract_for_job,
        ProcessingJobType.ATTRIBUTE_NORMALIZATION: normalization_service.normalize_for_job,
        ProcessingJobType.ATTRIBUTE_CONFLICT_DETECTION: conflict_service.detect_for_job,
        ProcessingJobType.ATTRIBUTE_COMPLETENESS: completeness_service.evaluate_for_job,
        ProcessingJobType.ATTRIBUTE_VALIDATION: validation_service.validate_for_job,
        ProcessingJobType.ATTRIBUTE_SELECTION: selection_service.select_for_job,
        ProcessingJobType.REVIEWED_ATTRIBUTE_MATERIALIZATION: (
            materialization_service.materialize_for_job
        ),
        ProcessingJobType.CATALOG_PROJECTION: projection_service.project_for_job,
        ProcessingJobType.CATALOG_EXPORT: export_service.export_for_job,
        ProcessingJobType.AI_CATALOG_ENRICHMENT: run_enrichment,
        ProcessingJobType.PRODUCT_INTELLIGENCE_SCORE: score_service.score_for_job,
    }
    loaders = {
        ProcessingJobType.PDF_TEXT_EXTRACTION: pdf_text.get_by_job_id,
        ProcessingJobType.PDF_TABLE_EXTRACTION: pdf_tables.get_by_job_id,
        ProcessingJobType.CSV_PROCESSING: csv_results.get_by_job_id,
        ProcessingJobType.IMAGE_ANALYSIS: image_analysis.get_by_job_id,
        ProcessingJobType.IMAGE_OCR: image_ocr.get_by_job_id,
        ProcessingJobType.PRODUCT_CLASSIFICATION: classifications.get_by_job_id,
        ProcessingJobType.ATTRIBUTE_EXTRACTION: extractions.get_by_job_id,
        ProcessingJobType.ATTRIBUTE_NORMALIZATION: normalizations.get_by_job_id,
        ProcessingJobType.ATTRIBUTE_CONFLICT_DETECTION: conflicts.get_by_job_id,
        ProcessingJobType.ATTRIBUTE_COMPLETENESS: completeness.get_by_job_id,
        ProcessingJobType.ATTRIBUTE_VALIDATION: validations.get_by_job_id,
        ProcessingJobType.ATTRIBUTE_SELECTION: selections.get_by_job_id,
        ProcessingJobType.REVIEWED_ATTRIBUTE_MATERIALIZATION: materializations.get_by_job_id,
        ProcessingJobType.CATALOG_PROJECTION: projections.get_by_job_id,
        ProcessingJobType.CATALOG_EXPORT: exports.get_by_job_id,
        ProcessingJobType.AI_CATALOG_ENRICHMENT: enrichments.get_by_job_id,
        ProcessingJobType.PRODUCT_INTELLIGENCE_SCORE: scores.get_by_job_id,
    }
    return ExistingServicesCatalogWorkflowStageExecutor(
        job_repository=jobs,
        product_repository=products,
        review_repository=reviews,
        projection_repository=projections,
        review_service=review_service,
        readiness_service=PublishingReadinessApplicationService(products, projections),
        runners=runners,
        result_loaders=loaders,
    )
