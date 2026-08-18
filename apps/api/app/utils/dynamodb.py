"""Central DynamoDB primitive and domain-item serialization."""

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, cast
from uuid import UUID

from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from pydantic import BaseModel

from app.core.exceptions import (
    CategoryAttributeSchemaSerializationError,
    CategoryAttributeSchemaValidationError,
    CsvProcessingSerializationError,
    ImageAnalysisSerializationError,
    ImageOcrSerializationError,
    PdfExtractionSerializationError,
    PdfTableExtractionSerializationError,
    ProcessingJobSerializationError,
    ProductClassificationSerializationError,
    ProductSerializationError,
    ProductSourceSerializationError,
)
from app.domain.category_schemas import (
    AttributeDataType,
    AttributeDefinition,
    AttributeValidationRules,
    CategoryAttributeSchema,
    CategoryAttributeSchemaStatus,
    UnitDefinition,
)
from app.domain.csv_processing import (
    CsvCell,
    CsvHeaderCell,
    CsvProcessingQualityStatus,
    CsvProcessingResult,
    CsvRow,
)
from app.domain.image_analysis import (
    ImageAnalysisRegion,
    ImageAnalysisResult,
    ImageMetadata,
    ImageOrientation,
    ImageRegionType,
    NameplateCandidateStatus,
)
from app.domain.image_ocr import (
    ImageOcrQualityStatus,
    ImageOcrResult,
    NameplateTextStatus,
    OcrTextBlock,
)
from app.domain.pdf_extraction import (
    PdfExtractionPage,
    PdfExtractionQualityStatus,
    PdfTextExtractionResult,
)
from app.domain.pdf_table_extraction import (
    PdfExtractedTable,
    PdfTableCell,
    PdfTableExtractionQualityStatus,
    PdfTableExtractionResult,
    PdfTableRow,
)
from app.domain.processing_jobs import ProcessingJob, ProcessingJobStatus, ProcessingJobType
from app.domain.product_classification import (
    ClassificationEvidenceType,
    ClassificationMatch,
    ClassificationSignalStrength,
    ProductClassificationResult,
    ProductClassificationStatus,
)
from app.domain.product_sources import ProductSource, ProductSourceStatus, ProductSourceType
from app.domain.products.entities import Product
from app.domain.products.enums import ProductCategory, ProductStatus

AttributeValue = dict[str, Any]
WireItem = dict[str, AttributeValue]


def format_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ProductSerializationError("timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ProductSerializationError("timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProductSerializationError("timestamp is not valid ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ProductSerializationError("timestamp must include a timezone")
    return parsed.astimezone(UTC)


def to_dynamodb_compatible(value: object) -> Any:
    """Recursively normalize supported values and reject Python floats."""
    if isinstance(value, float):
        raise ProductSerializationError("Python floats are not safe DynamoDB values")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return format_utc(value)
    if isinstance(value, Enum):
        return to_dynamodb_compatible(value.value)
    if value is None or isinstance(value, (str, int, bool, Decimal)):
        return value
    if isinstance(value, BaseModel):
        return to_dynamodb_compatible(value.model_dump())
    if is_dataclass(value) and not isinstance(value, type):
        return to_dynamodb_compatible(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): to_dynamodb_compatible(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [to_dynamodb_compatible(item) for item in value]
    raise ProductSerializationError(f"unsupported DynamoDB value type: {type(value).__name__}")


def serialize_item(item: Mapping[str, object]) -> WireItem:
    serializer = TypeSerializer()
    try:
        return {
            key: cast(AttributeValue, serializer.serialize(to_dynamodb_compatible(value)))
            for key, value in item.items()
        }
    except ProductSerializationError:
        raise
    except (TypeError, ValueError) as exc:
        raise ProductSerializationError("item could not be serialized for DynamoDB") from exc


def deserialize_item(item: Mapping[str, AttributeValue]) -> dict[str, Any]:
    deserializer = TypeDeserializer()
    try:
        return {key: deserializer.deserialize(value) for key, value in item.items()}
    except (TypeError, ValueError) as exc:
        raise ProductSerializationError("DynamoDB item has invalid attribute values") from exc


def product_to_item(product: Product) -> dict[str, object]:
    return {
        "productId": product.product_id,
        "entityType": "PRODUCT",
        "name": product.name,
        "manufacturer": product.manufacturer,
        "modelNumber": product.model_number,
        "category": product.category,
        "status": product.status,
        "description": product.description,
        "sourceCount": product.source_count,
        "version": product.version,
        "createdAt": product.created_at,
        "updatedAt": product.updated_at,
    }


def product_from_item(item: Mapping[str, object]) -> Product:
    try:
        if item.get("entityType") != "PRODUCT":
            raise ValueError("unexpected entity type")
        return Product(
            product_id=UUID(str(item["productId"])),
            name=_required_string(item["name"], "name"),
            manufacturer=_optional_string(item.get("manufacturer")),
            model_number=_optional_string(item.get("modelNumber")),
            category=ProductCategory(str(item["category"])),
            status=ProductStatus(str(item["status"])),
            description=_optional_string(item.get("description")),
            source_count=_integer(item["sourceCount"], "sourceCount"),
            version=_integer(item["version"], "version"),
            created_at=parse_utc(item["createdAt"]),
            updated_at=parse_utc(item["updatedAt"]),
        )
    except ProductSerializationError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductSerializationError("DynamoDB item is not a valid product") from exc


def product_source_to_item(source: ProductSource) -> dict[str, object]:
    return {
        "productId": source.product_id,
        "sourceId": source.source_id,
        "sourceType": source.source_type,
        "status": source.status,
        "originalFilename": source.original_filename,
        "storageKey": source.storage_key,
        "mimeType": source.mime_type,
        "fileSizeBytes": source.file_size_bytes,
        "checksumSha256": source.checksum_sha256,
        "displayName": source.display_name,
        "textContent": source.text_content,
        "errorMessage": source.error_message,
        "version": source.version,
        "createdAt": source.created_at,
        "updatedAt": source.updated_at,
    }


def product_source_from_item(item: Mapping[str, object]) -> ProductSource:
    try:
        return ProductSource(
            source_id=UUID(str(item["sourceId"])),
            product_id=UUID(str(item["productId"])),
            source_type=ProductSourceType(str(item["sourceType"])),
            status=ProductSourceStatus(str(item["status"])),
            original_filename=_optional_string(item.get("originalFilename")),
            storage_key=_optional_string(item.get("storageKey")),
            mime_type=_optional_string(item.get("mimeType")),
            file_size_bytes=_optional_integer(item.get("fileSizeBytes"), "fileSizeBytes"),
            checksum_sha256=_optional_string(item.get("checksumSha256")),
            display_name=_optional_string(item.get("displayName")),
            text_content=_optional_string(item.get("textContent")),
            error_message=_optional_string(item.get("errorMessage")),
            version=_integer(item["version"], "version"),
            created_at=parse_utc(item["createdAt"]),
            updated_at=parse_utc(item["updatedAt"]),
        )
    except ProductSourceSerializationError:
        raise
    except (KeyError, TypeError, ValueError, ProductSerializationError) as exc:
        raise ProductSourceSerializationError(
            "DynamoDB item is not a valid product source"
        ) from exc


def processing_job_source_scope(product_id: UUID, source_id: UUID) -> str:
    return f"{product_id}#{source_id}"


def processing_job_to_item(job: ProcessingJob) -> dict[str, object]:
    item: dict[str, object] = {
        "jobId": job.job_id,
        "productId": job.product_id,
        "jobType": job.job_type,
        "status": job.status,
        "attempt": job.attempt,
        "progressPercent": job.progress_percent,
        "errorCode": job.error_code,
        "errorMessage": job.error_message,
        "resultReference": job.result_reference,
        "version": job.version,
        "createdAt": job.created_at,
        "startedAt": job.started_at,
        "completedAt": job.completed_at,
        "updatedAt": job.updated_at,
    }
    if job.source_id is not None:
        item["sourceId"] = job.source_id
        item["sourceScope"] = processing_job_source_scope(job.product_id, job.source_id)
    if job.classification_id is not None:
        item["classificationId"] = job.classification_id
    if job.attribute_extraction_id is not None:
        item["attributeExtractionId"] = job.attribute_extraction_id
    if job.attribute_normalization_id is not None:
        item["attributeNormalizationId"] = job.attribute_normalization_id
    if job.attribute_conflict_detection_id is not None:
        item["attributeConflictDetectionId"] = job.attribute_conflict_detection_id
    if job.attribute_validation_id is not None:
        item["attributeValidationId"] = job.attribute_validation_id
    if job.attribute_completeness_id is not None:
        item["attributeCompletenessId"] = job.attribute_completeness_id
    if job.review_id is not None:
        item["reviewId"] = job.review_id
    if job.reviewed_attribute_materialization_id is not None:
        item["reviewedAttributeMaterializationId"] = job.reviewed_attribute_materialization_id
    if job.projection_id is not None:
        item["projectionId"] = job.projection_id
    return item


def processing_job_from_item(item: Mapping[str, object]) -> ProcessingJob:
    try:
        product_id = UUID(str(item["productId"]))
        source_id = UUID(str(item["sourceId"])) if "sourceId" in item else None
        if source_id is not None and item.get("sourceScope") != processing_job_source_scope(
            product_id, source_id
        ):
            raise ValueError("sourceScope does not match job ownership")
        if source_id is None and "sourceScope" in item:
            raise ValueError("sourceScope requires sourceId")
        return ProcessingJob(
            job_id=UUID(str(item["jobId"])),
            product_id=product_id,
            source_id=source_id,
            classification_id=(
                UUID(str(item["classificationId"])) if "classificationId" in item else None
            ),
            attribute_extraction_id=(
                UUID(str(item["attributeExtractionId"]))
                if "attributeExtractionId" in item
                else None
            ),
            attribute_normalization_id=(
                UUID(str(item["attributeNormalizationId"]))
                if "attributeNormalizationId" in item
                else None
            ),
            attribute_conflict_detection_id=(
                UUID(str(item["attributeConflictDetectionId"]))
                if "attributeConflictDetectionId" in item
                else None
            ),
            attribute_validation_id=(
                UUID(str(item["attributeValidationId"]))
                if "attributeValidationId" in item
                else None
            ),
            attribute_completeness_id=(
                UUID(str(item["attributeCompletenessId"]))
                if "attributeCompletenessId" in item
                else None
            ),
            review_id=(UUID(str(item["reviewId"])) if "reviewId" in item else None),
            reviewed_attribute_materialization_id=(
                UUID(str(item["reviewedAttributeMaterializationId"]))
                if "reviewedAttributeMaterializationId" in item
                else None
            ),
            projection_id=(UUID(str(item["projectionId"])) if "projectionId" in item else None),
            job_type=ProcessingJobType(str(item["jobType"])),
            status=ProcessingJobStatus(str(item["status"])),
            attempt=_integer(item["attempt"], "attempt"),
            progress_percent=_integer(item["progressPercent"], "progressPercent"),
            error_code=_optional_string(item.get("errorCode")),
            error_message=_optional_string(item.get("errorMessage")),
            result_reference=_optional_string(item.get("resultReference")),
            version=_integer(item["version"], "version"),
            created_at=parse_utc(item["createdAt"]),
            started_at=_optional_datetime(item.get("startedAt")),
            completed_at=_optional_datetime(item.get("completedAt")),
            updated_at=parse_utc(item["updatedAt"]),
        )
    except ProcessingJobSerializationError:
        raise
    except (KeyError, TypeError, ValueError, ProductSerializationError) as exc:
        raise ProcessingJobSerializationError(
            "DynamoDB item is not a valid processing job"
        ) from exc


def category_attribute_schema_to_item(schema: CategoryAttributeSchema) -> dict[str, object]:
    return {
        "category": schema.category,
        "version": schema.version,
        "schemaId": schema.schema_id,
        "status": schema.status,
        "description": schema.description,
        "attributes": [
            {
                "attributeId": attribute.attribute_id,
                "canonicalName": attribute.canonical_name,
                "displayName": attribute.display_name,
                "description": attribute.description,
                "dataType": attribute.data_type,
                "required": attribute.required,
                "allowedUnits": [
                    {
                        "symbol": unit.symbol,
                        "canonical": unit.canonical,
                        "dimension": unit.dimension,
                    }
                    for unit in attribute.allowed_units
                ],
                "aliases": attribute.aliases,
                "exampleValues": attribute.example_values,
                "validationRules": {
                    "minValue": attribute.validation_rules.min_value,
                    "maxValue": attribute.validation_rules.max_value,
                    "allowedValues": attribute.validation_rules.allowed_values,
                    "pattern": attribute.validation_rules.pattern,
                },
                "displayOrder": attribute.display_order,
            }
            for attribute in sorted(schema.attributes, key=lambda value: value.display_order)
        ],
        "schemaFingerprint": schema.schema_fingerprint,
        "createdAt": schema.created_at,
        "updatedAt": schema.updated_at,
    }


def _schema_sequence(value: object, field: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field} must be a sequence")
    return value


def _schema_mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")
    return cast(Mapping[str, object], value)


def _category_attribute_from_item(value: object) -> AttributeDefinition:
    item = _schema_mapping(value, "attribute")
    units = tuple(
        UnitDefinition(
            symbol=str(unit["symbol"]),
            canonical=str(unit["canonical"]),
            dimension=_optional_string(unit.get("dimension")),
        )
        for raw_unit in _schema_sequence(item["allowedUnits"], "allowedUnits")
        for unit in (_schema_mapping(raw_unit, "unit"),)
    )
    rules = _schema_mapping(item["validationRules"], "validationRules")
    return AttributeDefinition(
        attribute_id=str(item["attributeId"]),
        canonical_name=str(item["canonicalName"]),
        display_name=str(item["displayName"]),
        description=str(item["description"]),
        data_type=AttributeDataType(str(item["dataType"])),
        required=_boolean(item["required"], "required"),
        allowed_units=units,
        aliases=tuple(str(alias) for alias in _schema_sequence(item["aliases"], "aliases")),
        example_values=tuple(
            str(example) for example in _schema_sequence(item["exampleValues"], "exampleValues")
        ),
        validation_rules=AttributeValidationRules(
            min_value=cast(int | Decimal | None, rules.get("minValue")),
            max_value=cast(int | Decimal | None, rules.get("maxValue")),
            allowed_values=tuple(
                str(allowed)
                for allowed in _schema_sequence(rules["allowedValues"], "allowedValues")
            ),
            pattern=_optional_string(rules.get("pattern")),
        ),
        display_order=_integer(item["displayOrder"], "displayOrder"),
    )


def category_attribute_schema_from_item(item: Mapping[str, object]) -> CategoryAttributeSchema:
    try:
        return CategoryAttributeSchema(
            schema_id=str(item["schemaId"]),
            category=ProductCategory(str(item["category"])),
            version=_integer(item["version"], "version"),
            status=CategoryAttributeSchemaStatus(str(item["status"])),
            description=str(item["description"]),
            attributes=tuple(
                _category_attribute_from_item(attribute)
                for attribute in _schema_sequence(item["attributes"], "attributes")
            ),
            schema_fingerprint=str(item["schemaFingerprint"]),
            created_at=parse_utc(item["createdAt"]),
            updated_at=parse_utc(item["updatedAt"]),
        )
    except CategoryAttributeSchemaSerializationError:
        raise
    except (
        KeyError,
        TypeError,
        ValueError,
        ProductSerializationError,
        CategoryAttributeSchemaValidationError,
    ) as exc:
        raise CategoryAttributeSchemaSerializationError(
            "DynamoDB item is not a valid category attribute schema"
        ) from exc


def product_classification_metadata_to_item(
    result: ProductClassificationResult,
) -> dict[str, object]:
    return {
        "classificationId": result.classification_id,
        "recordKey": "META",
        "jobId": result.job_id,
        "productId": result.product_id,
        "category": result.category,
        "status": result.status,
        "confidenceBp": result.confidence_bp,
        "pumpScore": result.pump_score,
        "motorScore": result.motor_score,
        "evidenceItemCount": result.evidence_item_count,
        "matchedEvidenceCount": result.matched_evidence_count,
        "conflictingEvidenceCount": result.conflicting_evidence_count,
        "engine": result.engine,
        "engineVersion": result.engine_version,
        "warningCodes": result.warning_codes,
        "matchCount": len(result.matches),
        "createdAt": result.created_at,
    }


def product_classification_match_to_item(
    classification_id: UUID, index: int, match: ClassificationMatch
) -> dict[str, object]:
    return {
        "classificationId": classification_id,
        "recordKey": f"MATCH#{index:06d}",
        "matchId": match.match_id,
        "evidenceId": match.evidence_id,
        "sourceId": match.source_id,
        "evidenceType": match.evidence_type,
        "category": match.category,
        "matchedSignal": match.matched_signal,
        "signalStrength": match.signal_strength.name,
        "weightedScore": match.weighted_score,
        "location": match.location,
        "excerpt": match.excerpt,
    }


def product_classification_result_from_items(
    items: Sequence[Mapping[str, object]],
) -> ProductClassificationResult:
    try:
        metadata = next(item for item in items if item["recordKey"] == "META")
        records = sorted(
            (item for item in items if str(item["recordKey"]).startswith("MATCH#")),
            key=lambda item: str(item["recordKey"]),
        )
        matches = tuple(
            ClassificationMatch(
                match_id=str(item["matchId"]),
                evidence_id=str(item["evidenceId"]),
                source_id=UUID(str(item["sourceId"])),
                evidence_type=ClassificationEvidenceType(str(item["evidenceType"])),
                category=ProductCategory(str(item["category"])),
                matched_signal=str(item["matchedSignal"]),
                signal_strength=ClassificationSignalStrength[str(item["signalStrength"])],
                weighted_score=_integer(item["weightedScore"], "weightedScore"),
                location=str(item["location"]),
                excerpt=str(item["excerpt"]),
            )
            for item in records
        )
        if _integer(metadata["matchCount"], "matchCount") != len(matches):
            raise ValueError("matchCount does not match records")
        return ProductClassificationResult(
            classification_id=UUID(str(metadata["classificationId"])),
            job_id=UUID(str(metadata["jobId"])),
            product_id=UUID(str(metadata["productId"])),
            category=ProductCategory(str(metadata["category"])),
            status=ProductClassificationStatus(str(metadata["status"])),
            confidence_bp=_integer(metadata["confidenceBp"], "confidenceBp"),
            pump_score=_integer(metadata["pumpScore"], "pumpScore"),
            motor_score=_integer(metadata["motorScore"], "motorScore"),
            evidence_item_count=_integer(metadata["evidenceItemCount"], "evidenceItemCount"),
            matched_evidence_count=_integer(
                metadata["matchedEvidenceCount"], "matchedEvidenceCount"
            ),
            conflicting_evidence_count=_integer(
                metadata["conflictingEvidenceCount"], "conflictingEvidenceCount"
            ),
            matches=matches,
            warning_codes=tuple(
                str(code) for code in cast(Sequence[object], metadata["warningCodes"])
            ),
            engine=str(metadata["engine"]),
            engine_version=str(metadata["engineVersion"]),
            created_at=parse_utc(metadata["createdAt"]),
        )
    except (KeyError, StopIteration, TypeError, ValueError, ProductSerializationError) as exc:
        raise ProductClassificationSerializationError("classification records are invalid") from exc


def pdf_extraction_metadata_to_item(result: PdfTextExtractionResult) -> dict[str, object]:
    return {
        "extractionId": result.extraction_id,
        "recordKey": "META",
        "jobId": result.job_id,
        "productId": result.product_id,
        "sourceId": result.source_id,
        "parser": result.parser,
        "parserVersion": result.parser_version,
        "pageCount": result.page_count,
        "pagesWithText": result.pages_with_text,
        "totalCharacterCount": result.total_character_count,
        "qualityStatus": result.quality_status,
        "warningCodes": result.warning_codes,
        "createdAt": result.created_at,
    }


def pdf_extraction_page_to_item(extraction_id: UUID, page: PdfExtractionPage) -> dict[str, object]:
    return {
        "extractionId": extraction_id,
        "recordKey": f"PAGE#{page.page_number:06d}",
        "pageNumber": page.page_number,
        "text": page.text,
        "characterCount": page.character_count,
        "hasText": page.has_text,
    }


def pdf_extraction_result_from_items(
    items: Sequence[Mapping[str, object]],
) -> PdfTextExtractionResult:
    try:
        metadata_items = [item for item in items if item.get("recordKey") == "META"]
        if len(metadata_items) != 1:
            raise ValueError("one extraction metadata record is required")
        metadata = metadata_items[0]
        extraction_id = UUID(str(metadata["extractionId"]))
        page_items = sorted(
            (item for item in items if str(item.get("recordKey", "")).startswith("PAGE#")),
            key=lambda item: str(item["recordKey"]),
        )
        pages = tuple(
            PdfExtractionPage(
                page_number=_integer(item["pageNumber"], "pageNumber"),
                text=_required_string(item["text"], "text"),
                character_count=_integer(item["characterCount"], "characterCount"),
                has_text=_boolean(item["hasText"], "hasText"),
            )
            for item in page_items
        )
        warning_codes = metadata.get("warningCodes", [])
        if not isinstance(warning_codes, Sequence) or isinstance(warning_codes, (str, bytes)):
            raise ValueError("warningCodes must be a sequence")
        return PdfTextExtractionResult(
            extraction_id=extraction_id,
            job_id=UUID(str(metadata["jobId"])),
            product_id=UUID(str(metadata["productId"])),
            source_id=UUID(str(metadata["sourceId"])),
            parser=_required_string(metadata["parser"], "parser"),
            parser_version=_required_string(metadata["parserVersion"], "parserVersion"),
            page_count=_integer(metadata["pageCount"], "pageCount"),
            pages_with_text=_integer(metadata["pagesWithText"], "pagesWithText"),
            total_character_count=_integer(metadata["totalCharacterCount"], "totalCharacterCount"),
            quality_status=PdfExtractionQualityStatus(str(metadata["qualityStatus"])),
            pages=pages,
            warning_codes=tuple(_required_string(code, "warningCode") for code in warning_codes),
            created_at=parse_utc(metadata["createdAt"]),
        )
    except PdfExtractionSerializationError:
        raise
    except (KeyError, TypeError, ValueError, ProductSerializationError) as exc:
        raise PdfExtractionSerializationError(
            "DynamoDB items are not a valid PDF extraction result"
        ) from exc


def pdf_table_extraction_metadata_to_item(
    result: PdfTableExtractionResult,
) -> dict[str, object]:
    return {
        "extractionId": result.extraction_id,
        "recordKey": "META",
        "jobId": result.job_id,
        "productId": result.product_id,
        "sourceId": result.source_id,
        "parser": result.parser,
        "parserVersion": result.parser_version,
        "pageCount": result.page_count,
        "pagesWithTables": result.pages_with_tables,
        "tableCount": result.table_count,
        "totalRowCount": result.total_row_count,
        "totalCellCount": result.total_cell_count,
        "qualityStatus": result.quality_status,
        "warningCodes": result.warning_codes,
        "createdAt": result.created_at,
    }


def pdf_table_extraction_table_to_item(
    extraction_id: UUID, table: PdfExtractedTable
) -> dict[str, object]:
    return {
        "extractionId": extraction_id,
        "recordKey": f"TABLE#{table.page_number:06d}#{table.table_index:06d}",
        "pageNumber": table.page_number,
        "tableIndex": table.table_index,
        "rowCount": table.row_count,
        "columnCount": table.column_count,
        "cellCount": table.cell_count,
        "rows": [
            {
                "rowIndex": row.row_index,
                "cells": [
                    {
                        "rowIndex": cell.row_index,
                        "columnIndex": cell.column_index,
                        "text": cell.text,
                        "isEmpty": cell.is_empty,
                    }
                    for cell in row.cells
                ],
            }
            for row in table.rows
        ],
    }


def pdf_table_extraction_result_from_items(
    items: Sequence[Mapping[str, object]],
) -> PdfTableExtractionResult:
    try:
        metadata_items = [item for item in items if item.get("recordKey") == "META"]
        if len(metadata_items) != 1:
            raise ValueError("one table-extraction metadata record is required")
        metadata = metadata_items[0]
        extraction_id = UUID(str(metadata["extractionId"]))
        table_items = sorted(
            (item for item in items if str(item.get("recordKey", "")).startswith("TABLE#")),
            key=lambda item: str(item["recordKey"]),
        )
        tables = tuple(_pdf_extracted_table_from_item(item) for item in table_items)
        warnings = metadata.get("warningCodes", [])
        if not isinstance(warnings, Sequence) or isinstance(warnings, (str, bytes)):
            raise ValueError("warningCodes must be a sequence")
        return PdfTableExtractionResult(
            extraction_id=extraction_id,
            job_id=UUID(str(metadata["jobId"])),
            product_id=UUID(str(metadata["productId"])),
            source_id=UUID(str(metadata["sourceId"])),
            parser=_required_string(metadata["parser"], "parser"),
            parser_version=_required_string(metadata["parserVersion"], "parserVersion"),
            page_count=_integer(metadata["pageCount"], "pageCount"),
            pages_with_tables=_integer(metadata["pagesWithTables"], "pagesWithTables"),
            table_count=_integer(metadata["tableCount"], "tableCount"),
            total_row_count=_integer(metadata["totalRowCount"], "totalRowCount"),
            total_cell_count=_integer(metadata["totalCellCount"], "totalCellCount"),
            quality_status=PdfTableExtractionQualityStatus(str(metadata["qualityStatus"])),
            tables=tables,
            warning_codes=tuple(_required_string(code, "warningCode") for code in warnings),
            created_at=parse_utc(metadata["createdAt"]),
        )
    except PdfTableExtractionSerializationError:
        raise
    except (KeyError, TypeError, ValueError, ProductSerializationError) as exc:
        raise PdfTableExtractionSerializationError(
            "DynamoDB items are not a valid PDF table-extraction result"
        ) from exc


def _pdf_extracted_table_from_item(item: Mapping[str, object]) -> PdfExtractedTable:
    raw_rows = item["rows"]
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes)):
        raise ValueError("rows must be a sequence")
    rows: list[PdfTableRow] = []
    for raw_row in raw_rows:
        if not isinstance(raw_row, Mapping):
            raise ValueError("row must be a mapping")
        row_index = _integer(raw_row["rowIndex"], "rowIndex")
        raw_cells = raw_row["cells"]
        if not isinstance(raw_cells, Sequence) or isinstance(raw_cells, (str, bytes)):
            raise ValueError("cells must be a sequence")
        cells = tuple(
            PdfTableCell(
                row_index=_integer(cell["rowIndex"], "rowIndex"),
                column_index=_integer(cell["columnIndex"], "columnIndex"),
                text=_required_string(cell["text"], "text"),
                is_empty=_boolean(cell["isEmpty"], "isEmpty"),
            )
            for cell in raw_cells
            if isinstance(cell, Mapping)
        )
        if len(cells) != len(raw_cells):
            raise ValueError("cell must be a mapping")
        rows.append(PdfTableRow(row_index, cells))
    return PdfExtractedTable(
        table_index=_integer(item["tableIndex"], "tableIndex"),
        page_number=_integer(item["pageNumber"], "pageNumber"),
        row_count=_integer(item["rowCount"], "rowCount"),
        column_count=_integer(item["columnCount"], "columnCount"),
        cell_count=_integer(item["cellCount"], "cellCount"),
        rows=tuple(rows),
    )


def csv_processing_metadata_to_item(result: CsvProcessingResult) -> dict[str, object]:
    return {
        "processingId": result.processing_id,
        "recordKey": "META",
        "jobId": result.job_id,
        "productId": result.product_id,
        "sourceId": result.source_id,
        "encoding": result.encoding,
        "delimiter": result.delimiter,
        "header": [
            {"columnIndex": cell.column_index, "text": cell.text, "isEmpty": cell.is_empty}
            for cell in result.header
        ],
        "columnCount": result.column_count,
        "rowCount": result.row_count,
        "malformedRowCount": result.malformed_row_count,
        "emptyCellCount": result.empty_cell_count,
        "totalCellCount": result.total_cell_count,
        "qualityStatus": result.quality_status,
        "warningCodes": result.warning_codes,
        "createdAt": result.created_at,
    }


def csv_processing_row_to_item(processing_id: UUID, row: CsvRow) -> dict[str, object]:
    def cell_item(cell: CsvCell) -> dict[str, object]:
        return {"columnIndex": cell.column_index, "text": cell.text, "isEmpty": cell.is_empty}

    return {
        "processingId": processing_id,
        "recordKey": f"ROW#{row.row_number:09d}",
        "rowNumber": row.row_number,
        "cells": [cell_item(cell) for cell in row.cells],
        "extraCells": [cell_item(cell) for cell in row.extra_cells],
        "originalColumnCount": row.original_column_count,
        "normalizedColumnCount": row.normalized_column_count,
        "isMalformed": row.is_malformed,
        "warningCodes": row.warning_codes,
    }


def csv_processing_result_from_items(
    items: Sequence[Mapping[str, object]],
) -> CsvProcessingResult:
    try:
        metadata_items = [item for item in items if item.get("recordKey") == "META"]
        if len(metadata_items) != 1:
            raise ValueError("one CSV processing metadata record is required")
        metadata = metadata_items[0]
        processing_id = UUID(str(metadata["processingId"]))
        raw_header = metadata["header"]
        if not isinstance(raw_header, Sequence) or isinstance(raw_header, (str, bytes)):
            raise ValueError("header must be a sequence")
        header = tuple(_csv_header_cell_from_item(cell) for cell in raw_header)
        row_items = sorted(
            (item for item in items if str(item.get("recordKey", "")).startswith("ROW#")),
            key=lambda item: str(item["recordKey"]),
        )
        rows = tuple(_csv_row_from_item(item) for item in row_items)
        warnings = metadata.get("warningCodes", [])
        if not isinstance(warnings, Sequence) or isinstance(warnings, (str, bytes)):
            raise ValueError("warningCodes must be a sequence")
        return CsvProcessingResult(
            processing_id=processing_id,
            job_id=UUID(str(metadata["jobId"])),
            product_id=UUID(str(metadata["productId"])),
            source_id=UUID(str(metadata["sourceId"])),
            encoding=_required_string(metadata["encoding"], "encoding"),
            delimiter=_required_string(metadata["delimiter"], "delimiter"),
            header=header,
            column_count=_integer(metadata["columnCount"], "columnCount"),
            row_count=_integer(metadata["rowCount"], "rowCount"),
            malformed_row_count=_integer(metadata["malformedRowCount"], "malformedRowCount"),
            empty_cell_count=_integer(metadata["emptyCellCount"], "emptyCellCount"),
            total_cell_count=_integer(metadata["totalCellCount"], "totalCellCount"),
            quality_status=CsvProcessingQualityStatus(str(metadata["qualityStatus"])),
            rows=rows,
            warning_codes=tuple(_required_string(code, "warningCode") for code in warnings),
            created_at=parse_utc(metadata["createdAt"]),
        )
    except CsvProcessingSerializationError:
        raise
    except (KeyError, TypeError, ValueError, ProductSerializationError) as exc:
        raise CsvProcessingSerializationError(
            "DynamoDB items are not a valid CSV processing result"
        ) from exc


def _csv_header_cell_from_item(value: object) -> CsvHeaderCell:
    if not isinstance(value, Mapping):
        raise ValueError("header cell must be a mapping")
    return CsvHeaderCell(
        column_index=_integer(value["columnIndex"], "columnIndex"),
        text=_required_string(value["text"], "text"),
        is_empty=_boolean(value["isEmpty"], "isEmpty"),
    )


def _csv_cell_from_item(value: object) -> CsvCell:
    if not isinstance(value, Mapping):
        raise ValueError("CSV cell must be a mapping")
    return CsvCell(
        column_index=_integer(value["columnIndex"], "columnIndex"),
        text=_required_string(value["text"], "text"),
        is_empty=_boolean(value["isEmpty"], "isEmpty"),
    )


def _csv_row_from_item(item: Mapping[str, object]) -> CsvRow:
    raw_cells = item["cells"]
    raw_extra = item["extraCells"]
    warnings = item["warningCodes"]
    if not isinstance(raw_cells, Sequence) or isinstance(raw_cells, (str, bytes)):
        raise ValueError("cells must be a sequence")
    if not isinstance(raw_extra, Sequence) or isinstance(raw_extra, (str, bytes)):
        raise ValueError("extraCells must be a sequence")
    if not isinstance(warnings, Sequence) or isinstance(warnings, (str, bytes)):
        raise ValueError("warningCodes must be a sequence")
    return CsvRow(
        row_number=_integer(item["rowNumber"], "rowNumber"),
        cells=tuple(_csv_cell_from_item(cell) for cell in raw_cells),
        extra_cells=tuple(_csv_cell_from_item(cell) for cell in raw_extra),
        original_column_count=_integer(item["originalColumnCount"], "originalColumnCount"),
        normalized_column_count=_integer(item["normalizedColumnCount"], "normalizedColumnCount"),
        is_malformed=_boolean(item["isMalformed"], "isMalformed"),
        warning_codes=tuple(_required_string(code, "warningCode") for code in warnings),
    )


def image_analysis_metadata_to_item(result: ImageAnalysisResult) -> dict[str, object]:
    metadata = result.metadata
    return {
        "analysisId": result.analysis_id,
        "recordKey": "META",
        "jobId": result.job_id,
        "productId": result.product_id,
        "sourceId": result.source_id,
        "parser": result.parser,
        "parserVersion": result.parser_version,
        "format": metadata.format,
        "mimeType": metadata.mime_type,
        "width": metadata.width,
        "height": metadata.height,
        "pixelCount": metadata.pixel_count,
        "aspectRatioNumerator": metadata.aspect_ratio_numerator,
        "aspectRatioDenominator": metadata.aspect_ratio_denominator,
        "colorMode": metadata.color_mode,
        "hasAlpha": metadata.has_alpha,
        "isGrayscale": metadata.is_grayscale,
        "orientation": metadata.orientation,
        "fileSizeBytes": metadata.file_size_bytes,
        "nameplateCandidateStatus": result.nameplate_candidate_status,
        "heuristicScore": result.heuristic_score,
        "regionCount": len(result.regions),
        "warningCodes": result.warning_codes,
        "createdAt": result.created_at,
    }


def image_analysis_region_to_item(
    analysis_id: UUID, index: int, region: ImageAnalysisRegion
) -> dict[str, object]:
    return {
        "analysisId": analysis_id,
        "recordKey": f"REGION#{index:06d}",
        "regionId": region.region_id,
        "regionType": region.region_type,
        "x": region.x,
        "y": region.y,
        "width": region.width,
        "height": region.height,
        "relativeXBp": region.relative_x_bp,
        "relativeYBp": region.relative_y_bp,
        "relativeWidthBp": region.relative_width_bp,
        "relativeHeightBp": region.relative_height_bp,
        "heuristicScore": region.heuristic_score,
    }


def image_analysis_result_from_items(
    items: Sequence[Mapping[str, object]],
) -> ImageAnalysisResult:
    try:
        metadata_items = [item for item in items if item.get("recordKey") == "META"]
        if len(metadata_items) != 1:
            raise ValueError("one image-analysis metadata record is required")
        item = metadata_items[0]
        region_items = sorted(
            (value for value in items if str(value.get("recordKey", "")).startswith("REGION#")),
            key=lambda value: str(value["recordKey"]),
        )
        regions = tuple(_image_region_from_item(value) for value in region_items)
        warnings = item.get("warningCodes", [])
        if not isinstance(warnings, Sequence) or isinstance(warnings, (str, bytes)):
            raise ValueError("warningCodes must be a sequence")
        if _integer(item["regionCount"], "regionCount") != len(regions):
            raise ValueError("region count must match records")
        metadata = ImageMetadata(
            format=_required_string(item["format"], "format"),
            mime_type=_required_string(item["mimeType"], "mimeType"),
            width=_integer(item["width"], "width"),
            height=_integer(item["height"], "height"),
            pixel_count=_integer(item["pixelCount"], "pixelCount"),
            aspect_ratio_numerator=_integer(item["aspectRatioNumerator"], "aspectRatioNumerator"),
            aspect_ratio_denominator=_integer(
                item["aspectRatioDenominator"], "aspectRatioDenominator"
            ),
            color_mode=_required_string(item["colorMode"], "colorMode"),
            has_alpha=_boolean(item["hasAlpha"], "hasAlpha"),
            is_grayscale=_boolean(item["isGrayscale"], "isGrayscale"),
            orientation=ImageOrientation(str(item["orientation"])),
            file_size_bytes=_integer(item["fileSizeBytes"], "fileSizeBytes"),
        )
        return ImageAnalysisResult(
            analysis_id=UUID(str(item["analysisId"])),
            job_id=UUID(str(item["jobId"])),
            product_id=UUID(str(item["productId"])),
            source_id=UUID(str(item["sourceId"])),
            parser=_required_string(item["parser"], "parser"),
            parser_version=_required_string(item["parserVersion"], "parserVersion"),
            metadata=metadata,
            nameplate_candidate_status=NameplateCandidateStatus(
                str(item["nameplateCandidateStatus"])
            ),
            heuristic_score=_integer(item["heuristicScore"], "heuristicScore"),
            regions=regions,
            warning_codes=tuple(_required_string(code, "warningCode") for code in warnings),
            created_at=parse_utc(item["createdAt"]),
        )
    except ImageAnalysisSerializationError:
        raise
    except (KeyError, TypeError, ValueError, ProductSerializationError) as exc:
        raise ImageAnalysisSerializationError(
            "DynamoDB items are not a valid image-analysis result"
        ) from exc


def _image_region_from_item(item: Mapping[str, object]) -> ImageAnalysisRegion:
    return ImageAnalysisRegion(
        region_id=_required_string(item["regionId"], "regionId"),
        region_type=ImageRegionType(str(item["regionType"])),
        x=_integer(item["x"], "x"),
        y=_integer(item["y"], "y"),
        width=_integer(item["width"], "width"),
        height=_integer(item["height"], "height"),
        relative_x_bp=_integer(item["relativeXBp"], "relativeXBp"),
        relative_y_bp=_integer(item["relativeYBp"], "relativeYBp"),
        relative_width_bp=_integer(item["relativeWidthBp"], "relativeWidthBp"),
        relative_height_bp=_integer(item["relativeHeightBp"], "relativeHeightBp"),
        heuristic_score=_integer(item["heuristicScore"], "heuristicScore"),
    )


def image_ocr_metadata_to_item(result: ImageOcrResult) -> dict[str, object]:
    return {
        "ocrId": result.ocr_id,
        "recordKey": "META",
        "jobId": result.job_id,
        "productId": result.product_id,
        "sourceId": result.source_id,
        "imageAnalysisId": result.image_analysis_id,
        "engine": result.engine,
        "engineVersion": result.engine_version,
        "imageWidth": result.image_width,
        "imageHeight": result.image_height,
        "regionCount": result.region_count,
        "blockCount": result.block_count,
        "duplicateBlockCount": result.duplicate_block_count,
        "totalCharacterCount": result.total_character_count,
        "averageConfidenceBp": result.average_confidence_bp,
        "qualityStatus": result.quality_status,
        "nameplateTextStatus": result.nameplate_text_status,
        "nameplateHeuristicScore": result.nameplate_heuristic_score,
        "warningCodes": result.warning_codes,
        "createdAt": result.created_at,
    }


def image_ocr_block_to_item(ocr_id: UUID, index: int, block: OcrTextBlock) -> dict[str, object]:
    return {
        "ocrId": ocr_id,
        "recordKey": f"BLOCK#{index:06d}",
        "blockId": block.block_id,
        "regionId": block.region_id,
        "readingOrder": block.reading_order,
        "text": block.text,
        "confidenceBp": block.confidence_bp,
        "x": block.x,
        "y": block.y,
        "width": block.width,
        "height": block.height,
        "relativeXBp": block.relative_x_bp,
        "relativeYBp": block.relative_y_bp,
        "relativeWidthBp": block.relative_width_bp,
        "relativeHeightBp": block.relative_height_bp,
    }


def image_ocr_result_from_items(items: Sequence[Mapping[str, object]]) -> ImageOcrResult:
    try:
        metadata_items = [item for item in items if item.get("recordKey") == "META"]
        if len(metadata_items) != 1:
            raise ValueError("one image OCR metadata record is required")
        item = metadata_items[0]
        block_items = sorted(
            (value for value in items if str(value.get("recordKey", "")).startswith("BLOCK#")),
            key=lambda value: str(value["recordKey"]),
        )
        expected_count = _integer(item["blockCount"], "blockCount")
        if len(block_items) != expected_count or tuple(
            str(value["recordKey"]) for value in block_items
        ) != tuple(f"BLOCK#{index:06d}" for index in range(1, expected_count + 1)):
            raise ValueError("OCR block records must be complete and contiguous")
        warnings = item.get("warningCodes", [])
        if not isinstance(warnings, Sequence) or isinstance(warnings, (str, bytes)):
            raise ValueError("warningCodes must be a sequence")
        return ImageOcrResult(
            ocr_id=UUID(str(item["ocrId"])),
            job_id=UUID(str(item["jobId"])),
            product_id=UUID(str(item["productId"])),
            source_id=UUID(str(item["sourceId"])),
            image_analysis_id=UUID(str(item["imageAnalysisId"])),
            engine=_required_string(item["engine"], "engine"),
            engine_version=_required_string(item["engineVersion"], "engineVersion"),
            image_width=_integer(item["imageWidth"], "imageWidth"),
            image_height=_integer(item["imageHeight"], "imageHeight"),
            region_count=_integer(item["regionCount"], "regionCount"),
            block_count=expected_count,
            duplicate_block_count=_integer(item["duplicateBlockCount"], "duplicateBlockCount"),
            total_character_count=_integer(item["totalCharacterCount"], "totalCharacterCount"),
            average_confidence_bp=_integer(item["averageConfidenceBp"], "averageConfidenceBp"),
            quality_status=ImageOcrQualityStatus(str(item["qualityStatus"])),
            nameplate_text_status=NameplateTextStatus(str(item["nameplateTextStatus"])),
            nameplate_heuristic_score=_integer(
                item["nameplateHeuristicScore"], "nameplateHeuristicScore"
            ),
            blocks=tuple(_image_ocr_block_from_item(value) for value in block_items),
            warning_codes=tuple(_required_string(code, "warningCode") for code in warnings),
            created_at=parse_utc(item["createdAt"]),
        )
    except ImageOcrSerializationError:
        raise
    except (KeyError, TypeError, ValueError, ProductSerializationError) as exc:
        raise ImageOcrSerializationError("DynamoDB items are not a valid image OCR result") from exc


def _image_ocr_block_from_item(item: Mapping[str, object]) -> OcrTextBlock:
    return OcrTextBlock(
        block_id=_required_string(item["blockId"], "blockId"),
        region_id=_required_string(item["regionId"], "regionId"),
        reading_order=_integer(item["readingOrder"], "readingOrder"),
        text=_required_string(item["text"], "text"),
        confidence_bp=_integer(item["confidenceBp"], "confidenceBp"),
        x=_integer(item["x"], "x"),
        y=_integer(item["y"], "y"),
        width=_integer(item["width"], "width"),
        height=_integer(item["height"], "height"),
        relative_x_bp=_integer(item["relativeXBp"], "relativeXBp"),
        relative_y_bp=_integer(item["relativeYBp"], "relativeYBp"),
        relative_width_bp=_integer(item["relativeWidthBp"], "relativeWidthBp"),
        relative_height_bp=_integer(item["relativeHeightBp"], "relativeHeightBp"),
    )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional product text must be a string or null")
    return value


def _required_string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        raise ValueError(f"{field} must be an integer")
    integer = int(value)
    if Decimal(integer) != value:
        raise ValueError(f"{field} must be an integer")
    return integer


def _optional_integer(value: object, field: str) -> int | None:
    if value is None:
        return None
    return _integer(value, field)


def _optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    return parse_utc(value)


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")
    return value
