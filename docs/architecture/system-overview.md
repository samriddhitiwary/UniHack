# System Overview

The foundation has three independently runnable parts:

```text
Browser -> React/Vite application
              |
              v
        FastAPI /api/v1
              |
              v
       Repository interface
              |
              v
       DynamoDB repository -> DynamoDB Local (development)
                          -> Amazon DynamoDB (production configuration)
```

The frontend owns presentation and browser-side state. The API owns validated configuration and application behavior. Product and product-source domain models are independent of Boto3. Their repository protocols return domain entities, while DynamoDB implementations own item naming, serialization, conditional writes, index queries, and cursors.

The local products table supports repository development. SPEC-006 exposes create, list, retrieve, partial-update, and conditional-delete routes through this dependency chain:

```text
Product route -> ProductService -> ProductRepository protocol -> DynamoDBProductRepository
```

FastAPI providers construct the configured repository and service, so tests can replace the service without AWS. Routes never import Boto3 or instantiate repositories. The list service selects the existing creation-time or status access pattern, while cursor decoding and newest-first DynamoDB queries remain repository responsibilities. For PATCH, the service retrieves the immutable entity and merges only explicitly supplied editable fields; the repository owns conditional version comparison, version increment, and update timestamp. DELETE also performs a service pre-read, then the repository atomically requires the expected version to prevent a stale client from deleting newer data. There is no soft delete, restore, cascade, bulk operation, PUT replacement, or frontend product workflow; only DynamoDB infrastructure code may call Boto3.

SPEC-007 adds a backend-only product-source metadata foundation:

```text
Future source service -> ProductSourceRepository protocol -> DynamoDBProductSourceRepository
```

The source table groups records by product, lists them newest first through `ProductCreatedAtIndex`, and protects mutations with versions. Scoped opaque cursors prevent source-list cursors from crossing products or being reused as product-list cursors. No source service, API route, upload/storage implementation, extraction, processing job, or frontend source workflow exists yet.

SPEC-008 adds an independent backend-only object-storage foundation:

```text
Future source service -> ObjectStorage protocol -> LocalObjectStorage (development)
```

Logical keys, rather than filesystem paths, identify objects. The local backend streams bytes through bounded chunks, enforces the caller's maximum size, calculates SHA-256, prevents overwrite, and stores validated metadata sidecars. Every operation validates path safety and resolved-root containment. The settings-driven provider currently accepts only `local`; S3 remains a future backend. This layer does not create source records and is not exposed through an API.

SPEC-009 exposes one source workflow while keeping the storage foundation separate:

```text
POST text-source route
        |
        v
ProductSourceService
        |-- ProductRepository (parent existence)
        `-- ProductSourceRepository (TEXT metadata persistence)
```

The service validates the parent, computes UTF-8 size and SHA-256, and persists a `READY` text source through the existing DynamoDB repository. Routes contain no repository or checksum logic. The endpoint stores no file and does not call `ObjectStorage`. No source list, retrieve, update, delete, upload, or processing workflow exists.
