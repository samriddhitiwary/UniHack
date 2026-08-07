"""Product-source application service tests."""

import hashlib
import inspect
import io
from dataclasses import replace
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from app.core.exceptions import (
    InvalidProductSourceCursorError,
    InvalidProductSourceStatusTransitionError,
    ObjectNotFoundError,
    ObjectSizeExceededError,
    ObjectStorageError,
    ProductNotFoundError,
    ProductRepositoryError,
    ProductSourceAlreadyExistsError,
    ProductSourceNotFoundError,
    ProductSourceRepositoryError,
    ProductSourceStorageConsistencyError,
    ProductSourceVersionConflictError,
)
from app.domain.product_sources import (
    ProductSource,
    ProductSourcePage,
    ProductSourceStatus,
    ProductSourceType,
)
from app.domain.products import Product, ProductPage, ProductStatus
from app.repositories.product_sources import ProductSourceRepository
from app.repositories.products import ProductRepository
from app.schemas.product_sources import ProductSourceUpdate, TextProductSourceCreate
from app.services import product_sources as product_sources_module
from app.services.product_sources import ProductSourceService
from app.storage.models import StoredObject
from app.storage.protocol import ObjectStorage
from app.utils.file_validation import UploadSizeLimits
from tests.fixtures.product_sources import (
    SECOND_SOURCE_ID,
    SOURCE_ID,
    SOURCE_UPDATED_AT,
    make_product_source,
)
from tests.fixtures.products import PRODUCT_ID, make_product


class FakeProductRepository:
    def __init__(self, product: Product | None = None, error: Exception | None = None) -> None:
        self.product = product
        self.error = error
        self.requested_ids: list[UUID] = []

    def get_by_id(self, product_id: UUID) -> Product | None:
        self.requested_ids.append(product_id)
        if self.error is not None:
            raise self.error
        return self.product

    def create(self, product: Product) -> Product:
        raise NotImplementedError

    def update(self, product: Product, expected_version: int) -> Product:
        raise NotImplementedError

    def list_products(self, *, limit: int = 25, cursor: str | None = None) -> ProductPage:
        raise NotImplementedError

    def list_by_status(
        self, status: ProductStatus, *, limit: int = 25, cursor: str | None = None
    ) -> ProductPage:
        raise NotImplementedError

    def delete(self, product_id: UUID, expected_version: int) -> None:
        raise NotImplementedError


class FakeProductSourceRepository:
    def __init__(
        self,
        error: Exception | None = None,
        *,
        source: ProductSource | None = None,
        page: ProductSourcePage | None = None,
        update_error: Exception | None = None,
        delete_error: Exception | None = None,
    ) -> None:
        self.error = error
        self.source = source
        self.page = page or ProductSourcePage(items=(), next_cursor=None)
        self.update_error = update_error
        self.delete_error = delete_error
        self.created: list[ProductSource] = []
        self.requested_gets: list[tuple[UUID, UUID]] = []
        self.requested_lists: list[tuple[UUID, int, str | None]] = []
        self.update_calls: list[tuple[ProductSource, int]] = []
        self.delete_calls: list[tuple[UUID, UUID, int]] = []

    def create(self, source: ProductSource) -> ProductSource:
        self.created.append(source)
        if self.error is not None:
            raise self.error
        self.source = source
        return source

    def get_by_id(self, product_id: UUID, source_id: UUID) -> ProductSource | None:
        self.requested_gets.append((product_id, source_id))
        if self.error is not None:
            raise self.error
        if (
            self.source is None
            or self.source.product_id != product_id
            or self.source.source_id != source_id
        ):
            return None
        return self.source

    def update(self, source: ProductSource, expected_version: int) -> ProductSource:
        self.update_calls.append((source, expected_version))
        if self.update_error is not None:
            raise self.update_error
        updated = replace(source, updated_at=SOURCE_UPDATED_AT, version=expected_version + 1)
        self.source = updated
        return updated

    def list_by_product(
        self,
        product_id: UUID,
        *,
        limit: int = 25,
        cursor: str | None = None,
    ) -> ProductSourcePage:
        self.requested_lists.append((product_id, limit, cursor))
        if self.error is not None:
            raise self.error
        return self.page

    def delete(self, product_id: UUID, source_id: UUID, expected_version: int) -> None:
        self.delete_calls.append((product_id, source_id, expected_version))
        if self.delete_error is not None:
            raise self.delete_error
        self.source = None


def service(
    products: FakeProductRepository,
    sources: FakeProductSourceRepository,
    storage: "FakeStorage | None" = None,
) -> ProductSourceService:
    return ProductSourceService(
        cast(ProductRepository, products),
        cast(ProductSourceRepository, sources),
        cast(ObjectStorage, storage) if storage is not None else None,
        UploadSizeLimits(pdf=20, image=20, csv=20) if storage is not None else None,
    )


class FakeStorage:
    def __init__(
        self, error: Exception | None = None, delete_error: Exception | None = None
    ) -> None:
        self.error = error
        self.delete_error = delete_error
        self.saved: list[tuple[str, bytes, int]] = []
        self.deleted: list[str] = []

    def save(self, *, object_key: str, stream: object, max_size_bytes: int) -> StoredObject:
        if self.error is not None:
            raise self.error
        content = stream.read()  # type: ignore[attr-defined]
        if len(content) > max_size_bytes:
            raise ObjectSizeExceededError("too large")
        self.saved.append((object_key, content, max_size_bytes))
        return StoredObject(
            object_key=object_key,
            size_bytes=len(content),
            checksum_sha256=hashlib.sha256(content).hexdigest(),
            created_at=datetime.now(UTC),
        )

    def delete(self, object_key: str) -> None:
        self.deleted.append(object_key)
        if self.delete_error is not None:
            raise self.delete_error

    def open(self, object_key: str) -> object:
        raise NotImplementedError

    def exists(self, object_key: str) -> bool:
        return False

    def get_metadata(self, object_key: str) -> StoredObject:
        raise NotImplementedError


def test_create_text_source_checks_parent_and_builds_ready_metadata() -> None:
    products = FakeProductRepository(product=make_product())
    sources = FakeProductSourceRepository()
    request = TextProductSourceCreate(
        displayName="  Supplier notes  ",
        textContent="  Café pump\nPressure: 16 bar  ",
    )

    created = service(products, sources).create_text_source(PRODUCT_ID, request)

    normalized = "Café pump\nPressure: 16 bar"
    encoded = normalized.encode("utf-8")
    assert products.requested_ids == [PRODUCT_ID]
    assert sources.created == [created]
    assert created.product_id == PRODUCT_ID
    assert created.source_type is ProductSourceType.TEXT
    assert created.status is ProductSourceStatus.READY
    assert created.original_filename is None
    assert created.storage_key is None
    assert created.mime_type == "text/plain"
    assert created.file_size_bytes == len(encoded)
    assert created.checksum_sha256 == hashlib.sha256(encoded).hexdigest()
    assert created.display_name == "Supplier notes"
    assert created.text_content == normalized
    assert created.error_message is None
    assert created.version == 1
    assert created.source_id is not None
    assert created.created_at == created.updated_at


def test_empty_display_name_is_normalized_to_none() -> None:
    sources = FakeProductSourceRepository()
    request = TextProductSourceCreate(displayName="   ", textContent=" Model PX-400 ")
    created = service(FakeProductRepository(product=make_product()), sources).create_text_source(
        PRODUCT_ID, request
    )
    assert created.display_name is None
    assert created.text_content == "Model PX-400"


def test_missing_product_stops_before_source_repository() -> None:
    products = FakeProductRepository()
    sources = FakeProductSourceRepository()

    with pytest.raises(ProductNotFoundError) as captured:
        service(products, sources).create_text_source(
            PRODUCT_ID, TextProductSourceCreate(textContent="Model PX-400")
        )

    assert captured.value.product_id == str(PRODUCT_ID)
    assert products.requested_ids == [PRODUCT_ID]
    assert sources.created == []


def test_product_repository_failure_is_preserved_without_source_create() -> None:
    error = ProductRepositoryError("private product persistence detail")
    products = FakeProductRepository(error=error)
    sources = FakeProductSourceRepository()

    with pytest.raises(ProductRepositoryError) as captured:
        service(products, sources).create_text_source(
            PRODUCT_ID, TextProductSourceCreate(textContent="Model PX-400")
        )

    assert captured.value is error
    assert sources.created == []


@pytest.mark.parametrize(
    "error",
    [
        ProductSourceAlreadyExistsError("duplicate"),
        ProductSourceRepositoryError("private source persistence detail"),
    ],
)
def test_source_repository_controlled_failure_is_preserved(error: Exception) -> None:
    sources = FakeProductSourceRepository(error=error)

    with pytest.raises(type(error)) as captured:
        service(FakeProductRepository(product=make_product()), sources).create_text_source(
            PRODUCT_ID, TextProductSourceCreate(textContent="Model PX-400")
        )

    assert captured.value is error
    assert len(sources.created) == 1


def test_service_has_no_fastapi_boto3_or_direct_filesystem_dependency() -> None:
    source = inspect.getsource(product_sources_module)
    assert "fastapi" not in source
    assert "boto3" not in source
    assert "pathlib" not in source
    assert "LocalObjectStorage" not in source


def test_list_sources_checks_parent_and_preserves_newest_first_page() -> None:
    newest = make_product_source(source_id=SECOND_SOURCE_ID)
    older = make_product_source()
    products = FakeProductRepository(make_product())
    sources = FakeProductSourceRepository(
        page=ProductSourcePage(items=(newest, older), next_cursor="opaque-next")
    )

    result = service(products, sources).list_sources(
        product_id=PRODUCT_ID,
        limit=10,
        cursor="opaque-current",
    )

    assert products.requested_ids == [PRODUCT_ID]
    assert sources.requested_lists == [(PRODUCT_ID, 10, "opaque-current")]
    assert [item.source_id for item in result.items] == [SECOND_SOURCE_ID, SOURCE_ID]
    assert result.next_cursor == "opaque-next"


def test_list_sources_returns_empty_page() -> None:
    result = service(
        FakeProductRepository(make_product()), FakeProductSourceRepository()
    ).list_sources(product_id=PRODUCT_ID, limit=20)
    assert result.items == []
    assert result.next_cursor is None


def test_list_sources_missing_product_skips_source_repository() -> None:
    products = FakeProductRepository()
    sources = FakeProductSourceRepository()

    with pytest.raises(ProductNotFoundError):
        service(products, sources).list_sources(product_id=PRODUCT_ID, limit=20)

    assert products.requested_ids == [PRODUCT_ID]
    assert sources.requested_lists == []


def test_list_sources_preserves_product_repository_failure() -> None:
    error = ProductRepositoryError("private")
    sources = FakeProductSourceRepository()
    with pytest.raises(ProductRepositoryError) as captured:
        service(FakeProductRepository(error=error), sources).list_sources(
            product_id=PRODUCT_ID, limit=20
        )
    assert captured.value is error
    assert sources.requested_lists == []


@pytest.mark.parametrize(
    "error",
    [
        ProductSourceRepositoryError("private"),
        InvalidProductSourceCursorError("invalid"),
    ],
)
def test_list_sources_preserves_source_repository_failure(error: Exception) -> None:
    sources = FakeProductSourceRepository(error=error)
    with pytest.raises(type(error)) as captured:
        service(FakeProductRepository(make_product()), sources).list_sources(
            product_id=PRODUCT_ID, limit=20, cursor="opaque"
        )
    assert captured.value is error
    assert sources.requested_lists == [(PRODUCT_ID, 20, "opaque")]


def test_get_source_checks_parent_and_uses_composite_identity() -> None:
    expected = make_product_source()
    products = FakeProductRepository(make_product())
    sources = FakeProductSourceRepository(source=expected)

    result = service(products, sources).get_source(product_id=PRODUCT_ID, source_id=SOURCE_ID)

    assert result is expected
    assert products.requested_ids == [PRODUCT_ID]
    assert sources.requested_gets == [(PRODUCT_ID, SOURCE_ID)]


def test_get_source_missing_product_skips_source_repository() -> None:
    sources = FakeProductSourceRepository(source=make_product_source())
    with pytest.raises(ProductNotFoundError):
        service(FakeProductRepository(), sources).get_source(
            product_id=PRODUCT_ID, source_id=SOURCE_ID
        )
    assert sources.requested_gets == []


def test_get_source_missing_or_wrong_product_is_product_scoped() -> None:
    other_product_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    sources = FakeProductSourceRepository(source=make_product_source())

    with pytest.raises(ProductSourceNotFoundError) as captured:
        service(FakeProductRepository(make_product()), sources).get_source(
            product_id=other_product_id, source_id=SOURCE_ID
        )

    assert captured.value.product_id == str(other_product_id)
    assert captured.value.source_id == str(SOURCE_ID)
    assert sources.requested_gets == [(other_product_id, SOURCE_ID)]


def test_get_source_preserves_repository_failures() -> None:
    product_error = ProductRepositoryError("private product")
    sources = FakeProductSourceRepository()
    with pytest.raises(ProductRepositoryError) as captured_product:
        service(FakeProductRepository(error=product_error), sources).get_source(
            product_id=PRODUCT_ID, source_id=SOURCE_ID
        )
    assert captured_product.value is product_error
    assert sources.requested_gets == []

    source_error = ProductSourceRepositoryError("private source")
    failing_sources = FakeProductSourceRepository(error=source_error)
    with pytest.raises(ProductSourceRepositoryError) as captured_source:
        service(FakeProductRepository(make_product()), failing_sources).get_source(
            product_id=PRODUCT_ID, source_id=SOURCE_ID
        )
    assert captured_source.value is source_error


def test_update_source_merges_fields_and_preserves_immutable_metadata() -> None:
    current = make_product_source(status=ProductSourceStatus.READY, version=3)
    sources = FakeProductSourceRepository(source=current)
    request = ProductSourceUpdate(
        version=3,
        displayName=" Updated datasheet ",
        status=ProductSourceStatus.PROCESSING,
        errorMessage=" Tracking note ",
    )

    updated = service(FakeProductRepository(make_product()), sources).update_source(
        product_id=PRODUCT_ID,
        source_id=SOURCE_ID,
        request=request,
    )

    candidate, expected_version = sources.update_calls[0]
    assert expected_version == 3
    assert candidate.display_name == "Updated datasheet"
    assert candidate.status is ProductSourceStatus.PROCESSING
    assert candidate.error_message == "Tracking note"
    assert updated.version == 4
    assert updated.updated_at == SOURCE_UPDATED_AT
    assert (
        candidate.source_id,
        candidate.product_id,
        candidate.source_type,
        candidate.original_filename,
        candidate.storage_key,
        candidate.mime_type,
        candidate.file_size_bytes,
        candidate.checksum_sha256,
        candidate.text_content,
        candidate.created_at,
    ) == (
        current.source_id,
        current.product_id,
        current.source_type,
        current.original_filename,
        current.storage_key,
        current.mime_type,
        current.file_size_bytes,
        current.checksum_sha256,
        current.text_content,
        current.created_at,
    )


def test_update_source_explicit_null_clears_nullable_fields() -> None:
    current = make_product_source(
        status=ProductSourceStatus.FAILED,
        display_name="Old name",
        error_message="Old error",
    )
    sources = FakeProductSourceRepository(source=current)
    updated = service(FakeProductRepository(make_product()), sources).update_source(
        product_id=PRODUCT_ID,
        source_id=SOURCE_ID,
        request=ProductSourceUpdate(version=1, displayName=None, errorMessage=None),
    )
    assert updated.display_name is None
    assert updated.error_message is None
    assert updated.status is ProductSourceStatus.FAILED


def test_update_source_missing_fields_remain_unchanged_and_same_status_advances() -> None:
    current = make_product_source(
        status=ProductSourceStatus.READY,
        display_name="Kept",
        error_message="Kept error",
    )
    sources = FakeProductSourceRepository(source=current)
    updated = service(FakeProductRepository(make_product()), sources).update_source(
        product_id=PRODUCT_ID,
        source_id=SOURCE_ID,
        request=ProductSourceUpdate(version=1, status=ProductSourceStatus.READY),
    )
    assert updated.display_name == "Kept"
    assert updated.error_message == "Kept error"
    assert updated.status is ProductSourceStatus.READY
    assert updated.version == 2


@pytest.mark.parametrize(
    ("current_status", "requested_status"),
    [
        (ProductSourceStatus.FAILED, ProductSourceStatus.READY),
        (ProductSourceStatus.PROCESSING, ProductSourceStatus.COMPLETED),
    ],
)
def test_recovery_and_completion_clear_stale_error(
    current_status: ProductSourceStatus,
    requested_status: ProductSourceStatus,
) -> None:
    current = make_product_source(status=current_status, error_message="Stale error")
    sources = FakeProductSourceRepository(source=current)
    updated = service(FakeProductRepository(make_product()), sources).update_source(
        product_id=PRODUCT_ID,
        source_id=SOURCE_ID,
        request=ProductSourceUpdate(
            version=1,
            status=requested_status,
            errorMessage="Must also be cleared",
        ),
    )
    assert updated.status is requested_status
    assert updated.error_message is None


def test_invalid_status_transition_stops_before_repository_update() -> None:
    sources = FakeProductSourceRepository(
        source=make_product_source(status=ProductSourceStatus.READY)
    )
    with pytest.raises(InvalidProductSourceStatusTransitionError) as captured:
        service(FakeProductRepository(make_product()), sources).update_source(
            product_id=PRODUCT_ID,
            source_id=SOURCE_ID,
            request=ProductSourceUpdate(version=1, status=ProductSourceStatus.COMPLETED),
        )
    assert captured.value.source_id == str(SOURCE_ID)
    assert captured.value.current_status == "READY"
    assert captured.value.requested_status == "COMPLETED"
    assert sources.update_calls == []


def test_update_source_missing_parent_stops_before_source_lookup() -> None:
    sources = FakeProductSourceRepository(source=make_product_source())
    with pytest.raises(ProductNotFoundError):
        service(FakeProductRepository(), sources).update_source(
            product_id=PRODUCT_ID,
            source_id=SOURCE_ID,
            request=ProductSourceUpdate(version=1, displayName="Updated"),
        )
    assert sources.requested_gets == []
    assert sources.update_calls == []


def test_update_source_missing_or_cross_product_source_is_not_found() -> None:
    other_product_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    sources = FakeProductSourceRepository(source=make_product_source())
    with pytest.raises(ProductSourceNotFoundError):
        service(FakeProductRepository(make_product()), sources).update_source(
            product_id=other_product_id,
            source_id=SOURCE_ID,
            request=ProductSourceUpdate(version=1, displayName="Updated"),
        )
    assert sources.requested_gets == [(other_product_id, SOURCE_ID)]
    assert sources.update_calls == []


@pytest.mark.parametrize(
    "error",
    [
        ProductSourceVersionConflictError("stale"),
        ProductSourceRepositoryError("private"),
    ],
)
def test_update_source_preserves_controlled_update_errors(error: Exception) -> None:
    sources = FakeProductSourceRepository(source=make_product_source(), update_error=error)
    with pytest.raises(type(error)) as captured:
        service(FakeProductRepository(make_product()), sources).update_source(
            product_id=PRODUCT_ID,
            source_id=SOURCE_ID,
            request=ProductSourceUpdate(version=1, displayName="Updated"),
        )
    assert captured.value is error
    assert len(sources.update_calls) == 1


def test_update_source_preserves_product_and_source_read_failures() -> None:
    product_error = ProductRepositoryError("private product")
    sources = FakeProductSourceRepository(source=make_product_source())
    with pytest.raises(ProductRepositoryError):
        service(FakeProductRepository(error=product_error), sources).update_source(
            product_id=PRODUCT_ID,
            source_id=SOURCE_ID,
            request=ProductSourceUpdate(version=1, displayName="Updated"),
        )
    assert sources.requested_gets == []

    source_error = ProductSourceRepositoryError("private source")
    with pytest.raises(ProductSourceRepositoryError):
        service(
            FakeProductRepository(make_product()),
            FakeProductSourceRepository(error=source_error),
        ).update_source(
            product_id=PRODUCT_ID,
            source_id=SOURCE_ID,
            request=ProductSourceUpdate(version=1, displayName="Updated"),
        )


def test_update_source_method_has_no_http_infrastructure_or_storage_logic() -> None:
    source = inspect.getsource(ProductSourceService.update_source)
    for forbidden in ("fastapi", "boto3", "pathlib", "ObjectStorage", "_object_storage"):
        assert forbidden not in source


def text_source(*, version: int = 1) -> ProductSource:
    return make_product_source(
        source_type=ProductSourceType.TEXT,
        status=ProductSourceStatus.READY,
        original_filename=None,
        storage_key=None,
        mime_type="text/plain",
        file_size_bytes=4,
        checksum_sha256=hashlib.sha256(b"text").hexdigest(),
        text_content="text",
        version=version,
    )


def test_delete_text_source_skips_storage_and_deletes_metadata() -> None:
    storage = FakeStorage()
    sources = FakeProductSourceRepository(source=text_source(version=2))

    result = service(FakeProductRepository(make_product()), sources, storage).delete_source(
        product_id=PRODUCT_ID,
        source_id=SOURCE_ID,
        expected_version=2,
    )

    assert result is None
    assert storage.deleted == []
    assert sources.delete_calls == [(PRODUCT_ID, SOURCE_ID, 2)]
    assert sources.source is None


@pytest.mark.parametrize(
    ("source_type", "filename", "mime_type"),
    [
        (ProductSourceType.PDF, "source.pdf", "application/pdf"),
        (ProductSourceType.IMAGE, "source.png", "image/png"),
        (ProductSourceType.CSV, "source.csv", "text/csv"),
    ],
)
def test_delete_file_source_removes_object_then_metadata(
    source_type: ProductSourceType,
    filename: str,
    mime_type: str,
) -> None:
    key = f"products/{PRODUCT_ID}/sources/{SOURCE_ID}/{filename}"
    source = make_product_source(
        source_type=source_type,
        original_filename=filename,
        storage_key=key,
        mime_type=mime_type,
        version=3,
    )
    storage = FakeStorage()
    sources = FakeProductSourceRepository(source=source)

    service(FakeProductRepository(make_product()), sources, storage).delete_source(
        product_id=PRODUCT_ID,
        source_id=SOURCE_ID,
        expected_version=3,
    )

    assert storage.deleted == [key]
    assert sources.delete_calls == [(PRODUCT_ID, SOURCE_ID, 3)]


def test_delete_missing_parent_stops_source_storage_and_metadata_calls() -> None:
    storage = FakeStorage()
    sources = FakeProductSourceRepository(source=text_source())
    with pytest.raises(ProductNotFoundError):
        service(FakeProductRepository(), sources, storage).delete_source(
            product_id=PRODUCT_ID,
            source_id=SOURCE_ID,
            expected_version=1,
        )
    assert sources.requested_gets == []
    assert storage.deleted == []
    assert sources.delete_calls == []


def test_delete_missing_or_cross_product_source_is_scoped() -> None:
    other_product_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    storage = FakeStorage()
    sources = FakeProductSourceRepository(source=text_source())
    with pytest.raises(ProductSourceNotFoundError):
        service(FakeProductRepository(make_product()), sources, storage).delete_source(
            product_id=other_product_id,
            source_id=SOURCE_ID,
            expected_version=1,
        )
    assert sources.requested_gets == [(other_product_id, SOURCE_ID)]
    assert storage.deleted == []
    assert sources.delete_calls == []


def test_delete_stale_precheck_skips_storage_and_repository_delete() -> None:
    key = f"products/{PRODUCT_ID}/sources/{SOURCE_ID}/source.pdf"
    source = make_product_source(storage_key=key, version=4)
    storage = FakeStorage()
    sources = FakeProductSourceRepository(source=source)
    with pytest.raises(ProductSourceVersionConflictError):
        service(FakeProductRepository(make_product()), sources, storage).delete_source(
            product_id=PRODUCT_ID,
            source_id=SOURCE_ID,
            expected_version=3,
        )
    assert storage.deleted == []
    assert sources.delete_calls == []


def test_file_source_without_storage_key_is_controlled_consistency_failure() -> None:
    sources = FakeProductSourceRepository(source=make_product_source(storage_key=None))
    storage = FakeStorage()
    with pytest.raises(ProductSourceStorageConsistencyError):
        service(FakeProductRepository(make_product()), sources, storage).delete_source(
            product_id=PRODUCT_ID,
            source_id=SOURCE_ID,
            expected_version=1,
        )
    assert storage.deleted == []
    assert sources.delete_calls == []


@pytest.mark.parametrize(
    "error",
    [ObjectNotFoundError("missing"), ObjectStorageError("unavailable"), RuntimeError("unexpected")],
)
def test_storage_delete_failure_preserves_error_and_metadata(error: Exception) -> None:
    key = f"products/{PRODUCT_ID}/sources/{SOURCE_ID}/source.pdf"
    sources = FakeProductSourceRepository(source=make_product_source(storage_key=key))
    storage = FakeStorage(delete_error=error)
    with pytest.raises(type(error)) as captured:
        service(FakeProductRepository(make_product()), sources, storage).delete_source(
            product_id=PRODUCT_ID,
            source_id=SOURCE_ID,
            expected_version=1,
        )
    assert captured.value is error
    assert storage.deleted == [key]
    assert sources.delete_calls == []
    assert sources.source is not None


@pytest.mark.parametrize(
    "error",
    [
        ProductSourceRepositoryError("repository unavailable"),
        ProductSourceVersionConflictError("final race"),
        RuntimeError("unexpected"),
    ],
)
def test_repository_failure_after_object_delete_is_preserved_and_logged(
    error: Exception,
    caplog: pytest.LogCaptureFixture,
) -> None:
    key = f"products/{PRODUCT_ID}/sources/{SOURCE_ID}/source.pdf"
    sources = FakeProductSourceRepository(
        source=make_product_source(storage_key=key), delete_error=error
    )
    storage = FakeStorage()
    with pytest.raises(type(error)) as captured:
        service(FakeProductRepository(make_product()), sources, storage).delete_source(
            product_id=PRODUCT_ID,
            source_id=SOURCE_ID,
            expected_version=1,
        )
    assert captured.value is error
    assert storage.deleted == [key]
    assert sources.delete_calls == [(PRODUCT_ID, SOURCE_ID, 1)]
    assert "event=product_source.delete_consistency_risk" in caplog.text
    assert key not in caplog.text


def test_delete_preserves_product_and_source_read_failures() -> None:
    product_error = ProductRepositoryError("private product")
    sources = FakeProductSourceRepository(source=text_source())
    with pytest.raises(ProductRepositoryError):
        service(FakeProductRepository(error=product_error), sources).delete_source(
            product_id=PRODUCT_ID,
            source_id=SOURCE_ID,
            expected_version=1,
        )
    assert sources.requested_gets == []

    source_error = ProductSourceRepositoryError("private source")
    failing_sources = FakeProductSourceRepository(error=source_error)
    with pytest.raises(ProductSourceRepositoryError):
        service(FakeProductRepository(make_product()), failing_sources).delete_source(
            product_id=PRODUCT_ID,
            source_id=SOURCE_ID,
            expected_version=1,
        )
    assert failing_sources.delete_calls == []


def test_delete_source_method_has_no_http_concrete_storage_or_filesystem_logic() -> None:
    source = inspect.getsource(ProductSourceService.delete_source)
    for forbidden in (
        "fastapi",
        "boto3",
        "LocalObjectStorage",
        "pathlib",
        "unlink",
        "os.remove",
    ):
        assert forbidden not in source


@pytest.mark.parametrize(
    ("filename", "mime", "content", "source_type"),
    [
        ("pump.PDF", "application/pdf", b"%PDF-content", ProductSourceType.PDF),
        ("image.png", "image/png", b"\x89PNG\r\n\x1a\nbody", ProductSourceType.IMAGE),
        ("photo.jpeg", "image/jpeg", b"\xff\xd8\xffbody", ProductSourceType.IMAGE),
        ("photo.webp", "image/webp", b"RIFF1234WEBPbody", ProductSourceType.IMAGE),
        ("data.csv", "text/csv", b"name,value\npump,16\n", ProductSourceType.CSV),
    ],
)
def test_create_file_source_stores_complete_bytes_and_ready_metadata(
    filename: str, mime: str, content: bytes, source_type: ProductSourceType
) -> None:
    storage = FakeStorage()
    sources = FakeProductSourceRepository()
    created = service(FakeProductRepository(make_product()), sources, storage).create_file_source(
        product_id=PRODUCT_ID,
        stream=io.BytesIO(content),
        original_filename=filename,
        declared_mime_type=mime,
        display_name="  Upload  ",
    )
    key, saved, limit = storage.saved[0]
    assert saved == content
    assert limit == 20
    assert f"sources/{created.source_id}/" in key
    assert created.source_type is source_type
    assert created.status is ProductSourceStatus.READY
    assert created.original_filename.endswith(filename.split(".")[-1].lower())
    assert created.storage_key == key
    assert created.file_size_bytes == len(content)
    assert created.checksum_sha256 == hashlib.sha256(content).hexdigest()
    assert created.display_name == "Upload"
    assert created.text_content is None
    assert created.version == 1


def test_missing_product_skips_storage_and_source_repository() -> None:
    storage = FakeStorage()
    sources = FakeProductSourceRepository()
    with pytest.raises(ProductNotFoundError):
        service(FakeProductRepository(), sources, storage).create_file_source(
            product_id=PRODUCT_ID,
            stream=io.BytesIO(b"%PDF-x"),
            original_filename="x.pdf",
            declared_mime_type="application/pdf",
        )
    assert storage.saved == [] and sources.created == []


@pytest.mark.parametrize(
    "error",
    [
        ProductSourceAlreadyExistsError("duplicate"),
        ProductSourceRepositoryError("failure"),
        RuntimeError("unexpected"),
    ],
)
def test_persistence_failure_deletes_object_and_preserves_error(error: Exception) -> None:
    storage = FakeStorage()
    sources = FakeProductSourceRepository(error=error)
    with pytest.raises(type(error)) as captured:
        service(FakeProductRepository(make_product()), sources, storage).create_file_source(
            product_id=PRODUCT_ID,
            stream=io.BytesIO(b"%PDF-x"),
            original_filename="x.pdf",
            declared_mime_type="application/pdf",
        )
    assert captured.value is error
    assert storage.deleted == [storage.saved[0][0]]


def test_cleanup_failure_preserves_repository_error() -> None:
    original = ProductSourceRepositoryError("original")
    storage = FakeStorage(delete_error=ObjectStorageError("cleanup"))
    with pytest.raises(ProductSourceRepositoryError) as captured:
        service(
            FakeProductRepository(make_product()), FakeProductSourceRepository(original), storage
        ).create_file_source(
            product_id=PRODUCT_ID,
            stream=io.BytesIO(b"%PDF-x"),
            original_filename="x.pdf",
            declared_mime_type="application/pdf",
        )
    assert captured.value is original


def test_storage_failure_skips_source_repository() -> None:
    sources = FakeProductSourceRepository()
    error = ObjectStorageError("unavailable")
    with pytest.raises(ObjectStorageError):
        service(
            FakeProductRepository(make_product()), sources, FakeStorage(error=error)
        ).create_file_source(
            product_id=PRODUCT_ID,
            stream=io.BytesIO(b"%PDF-x"),
            original_filename="x.pdf",
            declared_mime_type="application/pdf",
        )
    assert sources.created == []
