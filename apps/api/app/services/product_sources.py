"""Product-source application workflows."""

import hashlib
import logging
from dataclasses import replace
from typing import BinaryIO
from uuid import UUID

from app.core.exceptions import (
    InvalidProductSourceStatusTransitionError,
    ProductNotFoundError,
    ProductRepositoryError,
    ProductSourceNotFoundError,
    ProductSourceRepositoryError,
    ProductSourceStorageConsistencyError,
    ProductSourceVersionConflictError,
)
from app.domain.product_sources import (
    ProductSource,
    ProductSourceStatus,
    ProductSourceType,
    is_status_transition_allowed,
)
from app.repositories.product_sources import ProductSourceRepository
from app.repositories.products import ProductRepository
from app.schemas.product_sources import (
    ProductSourceListResult,
    ProductSourceRecord,
    ProductSourceUpdate,
    TextProductSourceCreate,
)
from app.storage.keys import generate_object_key
from app.storage.protocol import ObjectStorage
from app.utils.file_validation import UploadSizeLimits, validate_upload

logger = logging.getLogger(__name__)

FILE_BACKED_SOURCE_TYPES = frozenset(
    {ProductSourceType.PDF, ProductSourceType.IMAGE, ProductSourceType.CSV}
)


class ProductSourceService:
    """Coordinate product-source use cases without HTTP or infrastructure coupling."""

    def __init__(
        self,
        product_repository: ProductRepository,
        source_repository: ProductSourceRepository,
        object_storage: ObjectStorage | None = None,
        upload_limits: UploadSizeLimits | None = None,
    ) -> None:
        self._product_repository = product_repository
        self._source_repository = source_repository
        self._object_storage = object_storage
        self._upload_limits = upload_limits

    def list_sources(
        self,
        *,
        product_id: UUID,
        limit: int,
        cursor: str | None = None,
    ) -> ProductSourceListResult:
        """List one product's source metadata newest first."""
        logger.info(
            "event=product_source.list.requested product_id=%s limit=%s has_cursor=%s",
            product_id,
            limit,
            cursor is not None,
        )
        self._require_product(product_id)
        try:
            page = self._source_repository.list_by_product(
                product_id,
                limit=limit,
                cursor=cursor,
            )
        except ProductSourceRepositoryError as exc:
            logger.warning(
                "event=product_source.read_failed product_id=%s operation=list error_type=%s",
                product_id,
                type(exc).__name__,
            )
            raise
        result = ProductSourceListResult(
            items=[ProductSourceRecord.model_validate(source) for source in page.items],
            next_cursor=page.next_cursor,
        )
        logger.info(
            "event=product_source.listed product_id=%s limit=%s result_count=%s has_next_cursor=%s",
            product_id,
            limit,
            len(result.items),
            result.next_cursor is not None,
        )
        return result

    def get_source(self, *, product_id: UUID, source_id: UUID) -> ProductSource:
        """Retrieve one source by its product-scoped composite identity."""
        logger.info(
            "event=product_source.retrieve.requested product_id=%s source_id=%s",
            product_id,
            source_id,
        )
        self._require_product(product_id)
        try:
            source = self._source_repository.get_by_id(product_id, source_id)
        except ProductSourceRepositoryError as exc:
            logger.warning(
                "event=product_source.read_failed product_id=%s source_id=%s "
                "operation=retrieve error_type=%s",
                product_id,
                source_id,
                type(exc).__name__,
            )
            raise
        if source is None:
            logger.info(
                "event=product_source.not_found product_id=%s source_id=%s",
                product_id,
                source_id,
            )
            raise ProductSourceNotFoundError(product_id, source_id)
        logger.info(
            "event=product_source.retrieved product_id=%s source_id=%s",
            product_id,
            source_id,
        )
        return source

    def _require_product(self, product_id: UUID) -> None:
        try:
            product = self._product_repository.get_by_id(product_id)
        except ProductRepositoryError as exc:
            logger.warning(
                "event=product_source.read_failed product_id=%s operation=parent_check "
                "error_type=%s",
                product_id,
                type(exc).__name__,
            )
            raise
        if product is None:
            logger.info("event=product_source.parent_product_not_found product_id=%s", product_id)
            raise ProductNotFoundError(product_id)

    def update_source(
        self,
        *,
        product_id: UUID,
        source_id: UUID,
        request: ProductSourceUpdate,
    ) -> ProductSource:
        """Update approved source fields using product scope and optimistic concurrency."""
        updated_fields = request.model_fields_set & request.editable_fields
        logger.info(
            "event=product_source.update.requested product_id=%s source_id=%s "
            "expected_version=%s fields=%s",
            product_id,
            source_id,
            request.version,
            ",".join(sorted(updated_fields)),
        )
        self._require_product(product_id)
        try:
            current = self._source_repository.get_by_id(product_id, source_id)
        except ProductSourceRepositoryError as exc:
            logger.warning(
                "event=product_source.update_failed product_id=%s source_id=%s "
                "expected_version=%s operation=retrieve error_type=%s",
                product_id,
                source_id,
                request.version,
                type(exc).__name__,
            )
            raise
        if current is None:
            logger.info(
                "event=product_source.update_not_found product_id=%s source_id=%s",
                product_id,
                source_id,
            )
            raise ProductSourceNotFoundError(product_id, source_id)

        requested_status = request.status if "status" in updated_fields else None
        if requested_status is not None and not is_status_transition_allowed(
            current.status, requested_status
        ):
            logger.info(
                "event=product_source.status_transition_rejected product_id=%s source_id=%s "
                "current_status=%s requested_status=%s",
                product_id,
                source_id,
                current.status.value,
                requested_status.value,
            )
            raise InvalidProductSourceStatusTransitionError(
                source_id,
                current.status.value,
                requested_status.value,
            )

        changes = request.model_dump(
            include=updated_fields,
            exclude_unset=True,
            by_alias=False,
        )
        if (current.status, requested_status) in {
            (ProductSourceStatus.FAILED, ProductSourceStatus.READY),
            (ProductSourceStatus.PROCESSING, ProductSourceStatus.COMPLETED),
        }:
            changes["error_message"] = None
        candidate = replace(current, **changes)
        try:
            stored = self._source_repository.update(
                candidate,
                expected_version=request.version,
            )
        except ProductSourceVersionConflictError:
            logger.info(
                "event=product_source.update_version_conflict product_id=%s source_id=%s "
                "expected_version=%s",
                product_id,
                source_id,
                request.version,
            )
            raise
        except ProductSourceRepositoryError as exc:
            logger.warning(
                "event=product_source.update_failed product_id=%s source_id=%s "
                "expected_version=%s operation=update error_type=%s",
                product_id,
                source_id,
                request.version,
                type(exc).__name__,
            )
            raise
        logger.info(
            "event=product_source.updated product_id=%s source_id=%s version=%s status=%s "
            "fields=%s",
            product_id,
            source_id,
            stored.version,
            stored.status.value,
            ",".join(sorted(updated_fields)),
        )
        return stored

    def delete_source(
        self,
        *,
        product_id: UUID,
        source_id: UUID,
        expected_version: int,
    ) -> None:
        """Delete one source and its file object with optimistic concurrency."""
        logger.info(
            "event=product_source.delete.requested product_id=%s source_id=%s expected_version=%s",
            product_id,
            source_id,
            expected_version,
        )
        self._require_product(product_id)
        try:
            source = self._source_repository.get_by_id(product_id, source_id)
        except ProductSourceRepositoryError as exc:
            logger.warning(
                "event=product_source.delete_failed product_id=%s source_id=%s "
                "expected_version=%s operation=retrieve error_type=%s",
                product_id,
                source_id,
                expected_version,
                type(exc).__name__,
            )
            raise
        if source is None:
            logger.info(
                "event=product_source.delete_not_found product_id=%s source_id=%s",
                product_id,
                source_id,
            )
            raise ProductSourceNotFoundError(product_id, source_id)
        if source.version != expected_version:
            logger.info(
                "event=product_source.delete_version_conflict product_id=%s source_id=%s "
                "expected_version=%s current_version=%s stage=precheck",
                product_id,
                source_id,
                expected_version,
                source.version,
            )
            raise ProductSourceVersionConflictError("product source version is stale")

        object_deleted = False
        if source.source_type in FILE_BACKED_SOURCE_TYPES:
            if source.storage_key is None or self._object_storage is None:
                raise ProductSourceStorageConsistencyError(
                    product_id,
                    source_id,
                    source.source_type.value,
                )
            logger.info(
                "event=product_source.delete_object_started product_id=%s source_id=%s "
                "source_type=%s expected_version=%s",
                product_id,
                source_id,
                source.source_type.value,
                expected_version,
            )
            try:
                self._object_storage.delete(source.storage_key)
            except Exception as exc:
                logger.warning(
                    "event=product_source.delete_failed product_id=%s source_id=%s "
                    "source_type=%s expected_version=%s operation=object_delete error_type=%s",
                    product_id,
                    source_id,
                    source.source_type.value,
                    expected_version,
                    type(exc).__name__,
                )
                raise
            object_deleted = True
            logger.info(
                "event=product_source.delete_object_completed product_id=%s source_id=%s "
                "source_type=%s expected_version=%s",
                product_id,
                source_id,
                source.source_type.value,
                expected_version,
            )

        try:
            self._source_repository.delete(product_id, source_id, expected_version)
        except Exception as exc:
            if object_deleted:
                logger.error(
                    "event=product_source.delete_consistency_risk product_id=%s source_id=%s "
                    "source_type=%s expected_version=%s error_type=%s",
                    product_id,
                    source_id,
                    source.source_type.value,
                    expected_version,
                    type(exc).__name__,
                )
            else:
                logger.warning(
                    "event=product_source.delete_failed product_id=%s source_id=%s "
                    "source_type=%s expected_version=%s operation=metadata_delete error_type=%s",
                    product_id,
                    source_id,
                    source.source_type.value,
                    expected_version,
                    type(exc).__name__,
                )
            raise
        logger.info(
            "event=product_source.deleted product_id=%s source_id=%s source_type=%s "
            "expected_version=%s object_deleted=%s",
            product_id,
            source_id,
            source.source_type.value,
            expected_version,
            object_deleted,
        )

    def create_text_source(
        self,
        product_id: UUID,
        request: TextProductSourceCreate,
    ) -> ProductSource:
        """Attach normalized plain text to an existing product."""
        content = request.text_content.encode("utf-8")
        logger.info(
            "event=product_source.text_create.requested product_id=%s "
            "size_bytes=%s has_display_name=%s",
            product_id,
            len(content),
            request.display_name is not None,
        )
        try:
            product = self._product_repository.get_by_id(product_id)
        except ProductRepositoryError as exc:
            logger.warning(
                "event=product_source.text_create_failed product_id=%s error_type=%s",
                product_id,
                type(exc).__name__,
            )
            raise
        if product is None:
            logger.info(
                "event=product_source.parent_product_not_found product_id=%s",
                product_id,
            )
            raise ProductNotFoundError(product_id)

        source = ProductSource.create(
            product_id=product_id,
            source_type=ProductSourceType.TEXT,
            original_filename=None,
            storage_key=None,
            mime_type="text/plain",
            file_size_bytes=len(content),
            checksum_sha256=hashlib.sha256(content).hexdigest(),
            display_name=request.display_name,
            text_content=request.text_content,
        )
        source = replace(source, status=ProductSourceStatus.READY)
        try:
            stored = self._source_repository.create(source)
        except ProductSourceRepositoryError as exc:
            logger.warning(
                "event=product_source.text_create_failed product_id=%s source_id=%s error_type=%s",
                product_id,
                source.source_id,
                type(exc).__name__,
            )
            raise
        logger.info(
            "event=product_source.text_created product_id=%s source_id=%s "
            "source_type=%s size_bytes=%s",
            stored.product_id,
            stored.source_id,
            stored.source_type.value,
            stored.file_size_bytes,
        )
        return stored

    def create_file_source(
        self,
        *,
        product_id: UUID,
        stream: BinaryIO,
        original_filename: str | None,
        declared_mime_type: str | None,
        display_name: str | None = None,
    ) -> ProductSource:
        """Validate, store, and persist one supported file source."""
        logger.info(
            "event=product_source.upload.requested product_id=%s has_display_name=%s",
            product_id,
            bool(display_name and display_name.strip()),
        )
        product = self._product_repository.get_by_id(product_id)
        if product is None:
            logger.info("event=product_source.parent_product_not_found product_id=%s", product_id)
            raise ProductNotFoundError(product_id)
        if self._object_storage is None or self._upload_limits is None:
            raise RuntimeError("file-upload dependencies are unavailable")

        upload = validate_upload(
            stream=stream,
            original_filename=original_filename,
            declared_mime_type=declared_mime_type,
            limits=self._upload_limits,
        )
        source = ProductSource.create(
            product_id=product_id,
            source_type=upload.source_type,
            original_filename=upload.original_filename,
            mime_type=upload.mime_type,
            display_name=display_name,
        )
        object_key = generate_object_key(
            product_id=product_id,
            source_id=source.source_id,
            original_filename=upload.original_filename,
        )
        logger.info(
            "event=product_source.upload_validated product_id=%s source_id=%s "
            "source_type=%s extension=%s",
            product_id,
            source.source_id,
            upload.source_type.value,
            upload.extension,
        )
        stored_object = self._object_storage.save(
            object_key=object_key,
            stream=upload.stream,
            max_size_bytes=upload.max_size_bytes,
        )
        source = replace(
            source,
            status=ProductSourceStatus.READY,
            storage_key=stored_object.object_key,
            file_size_bytes=stored_object.size_bytes,
            checksum_sha256=stored_object.checksum_sha256,
        )
        logger.info(
            "event=product_source.object_saved product_id=%s source_id=%s size_bytes=%s",
            product_id,
            source.source_id,
            stored_object.size_bytes,
        )
        try:
            created = self._source_repository.create(source)
        except Exception:
            logger.warning(
                "event=product_source.upload_cleanup_started product_id=%s source_id=%s",
                product_id,
                source.source_id,
            )
            try:
                self._object_storage.delete(stored_object.object_key)
                logger.info(
                    "event=product_source.upload_cleanup_completed product_id=%s source_id=%s",
                    product_id,
                    source.source_id,
                )
            except Exception as cleanup_error:
                logger.error(
                    "event=product_source.upload_cleanup_failed product_id=%s source_id=%s "
                    "error_type=%s",
                    product_id,
                    source.source_id,
                    type(cleanup_error).__name__,
                )
            raise
        logger.info(
            "event=product_source.file_created product_id=%s source_id=%s "
            "source_type=%s size_bytes=%s",
            product_id,
            created.source_id,
            created.source_type.value,
            created.file_size_bytes,
        )
        return created
