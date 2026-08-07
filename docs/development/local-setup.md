# Local Development

Copy all three `.env.example` files, install dependencies as shown in the root README, and start DynamoDB Local with `docker compose up -d dynamodb-local`.

The API storage settings are:

```env
STORAGE_BACKEND=local
LOCAL_STORAGE_ROOT=../../storage
```

Relative storage paths resolve from `apps/api`, making the example root the repository's `storage` directory. The directory is created when the storage dependency is first requested. Generated runtime objects under `storage/products` are ignored by Git. A path that points to a file fails configuration instead of using the process directory. Local object persistence is development-only and must not be treated as durable Lambda storage. `s3` is not implemented and is rejected explicitly.

Upload byte limits use `MAX_PDF_UPLOAD_BYTES` and `MAX_IMAGE_UPLOAD_BYTES` (10 MiB defaults) plus `MAX_CSV_UPLOAD_BYTES` (5 MiB default). Every value must be positive.

Create the local products and product-sources tables with:

```powershell
uv run --project apps/api python scripts/dynamodb/create_tables.py
```

The equivalent command is `make dynamodb-create-tables`. It is safe to rerun and does not delete existing products.

Useful PowerShell commands:

```powershell
docker compose logs -f dynamodb-local
docker compose down
uv run --project apps/api pytest apps/api/tests
npm --prefix apps/web test -- --run
```

`/api/v1/health` proves the process is alive. `/api/v1/health/ready` also requires DynamoDB to answer. A 503 readiness response normally means Docker is stopped, port 8001 is unavailable, or the configured endpoint is wrong.

DynamoDB Local persists its database under `infrastructure/docker/dynamodb`, matching AWS's current Docker Compose guidance. The directory is ignored by Git. `make dynamodb-reset` removes the service's local data through the reset helper before restarting it.
