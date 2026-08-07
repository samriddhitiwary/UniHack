# Object Storage

SPEC-008 provides a backend-only binary object boundary:

```text
Future source service
        |
        v
ObjectStorage protocol
        |
        v
LocalObjectStorage (development)
```

No upload route, product-source workflow, S3 backend, URL generation, content inspection, or processing behavior is part of this foundation.

## Contract

Application code can depend on five provider-independent operations:

- `save(object_key=..., stream=..., max_size_bytes=...)` streams bytes and returns metadata.
- `open(object_key)` returns a caller-owned binary readable stream.
- `exists(object_key)` returns `True` only for a regular, non-symbolic-link object.
- `get_metadata(object_key)` returns metadata without reading object content.
- `delete(object_key)` removes exactly one object and its sidecar.

`StoredObject` is immutable and contains only `object_key`, `size_bytes`, `checksum_sha256`, and an aware UTC `created_at`. Public operations never return a local path.

## Logical keys

The key generator produces:

```text
products/{product UUID}/sources/{source UUID}/{random UUID}{extension}
```

Only `.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`, and `.csv` are accepted, and the extension is lowercase. The original filename is not retained in the stored filename. Keys always use `/`, including on Windows.

All operations reject blank or over-1,024-character keys, absolute paths, Windows drive paths, URL schemes, backslashes, null/control characters, `.` or `..`, empty or malformed segments, internal sidecar/temp names, and resolved paths outside the storage root. Root containment uses resolved path comparison, not string prefixes. Directories and symbolic links are not objects.

## Local writes and metadata

`LocalObjectStorage` reads supplied streams in 256 KiB chunks. It tracks actual bytes and computes SHA-256 in the same pass, so object size does not determine memory use. A positive caller-provided maximum is enforced while reading: zero-byte objects and exact-limit objects succeed, while an object over the limit fails without a final or temporary object.

The implementation writes object data and strict UTF-8 JSON metadata to random temporary files in the destination directory. It exclusively reserves both final names with mode-restricted empty files and then atomically replaces those reservations with the completed temporary files. This prevents an existing object or sidecar from being overwritten without creating filesystem hard links. A finalization failure removes reservations, any final file created by that save, and temporary files.

The deterministic sidecar suffix is `.metadata.json`. Sidecars contain camelCase object key, size, checksum, and UTC creation timestamp; they contain no local path, original filename, credentials, or content. Metadata retrieval validates the exact JSON shape, field invariants, object-key match, and current object size. Missing, malformed, or inconsistent metadata raises a controlled error.

## Configuration

```env
STORAGE_BACKEND=local
LOCAL_STORAGE_ROOT=../../storage
```

Relative roots are resolved from the `apps/api` project directory, so the example selects the repository's `storage` directory. The provider creates the directory when first constructed, not at module import. A root that is a file or cannot be created fails with `ObjectStorageConfigurationError`. The provider caches one safe process-wide instance and exposes a separate factory for isolated tests.

`s3` is reserved in settings for a future implementation but is currently rejected rather than falling back to local storage.

## Operational boundary

Local persistence is for development and tests only. Future AWS/Lambda deployments must use a durable provider such as S3; Lambda local files are not application persistence. Storage logs include only the backend, first logical-key category, sizes, and at most a checksum prefix. They exclude full keys, roots, paths, original filenames, file bytes, and raw filesystem errors.
