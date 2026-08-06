# Local Development

Copy all three `.env.example` files, install dependencies as shown in the root README, and start DynamoDB Local with `docker compose up -d dynamodb-local`.

Create the SPEC-002 local products table with:

```powershell
uv run --project apps/api python scripts/dynamodb/create_tables.py
```

The equivalent command is `make dynamodb-create-tables`. It is safe to rerun and does not delete existing products.

Useful PowerShell commands:

```powershell
docker compose logs -f dynamodb-local
docker compose down
docker compose down
uv run --project apps/api pytest apps/api/tests
npm --prefix apps/web test -- --run
```

`/api/v1/health` proves the process is alive. `/api/v1/health/ready` also requires DynamoDB to answer. A 503 readiness response normally means Docker is stopped, port 8001 is unavailable, or the configured endpoint is wrong.

DynamoDB Local persists its database under `infrastructure/docker/dynamodb`, matching AWS's current Docker Compose guidance. The directory is ignored by Git. `make dynamodb-reset` removes the service's local data through the reset helper before restarting it.
