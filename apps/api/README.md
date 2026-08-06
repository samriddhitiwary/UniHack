# CatalogIQ API

FastAPI and Mangum foundation for Python 3.12. From the repository root:

```powershell
uv sync --project apps/api --all-groups
uv run --project apps/api uvicorn app.main:app --reload --app-dir apps/api
```

Run checks with `uv run --project apps/api pytest apps/api/tests`, `uv run --project apps/api ruff check apps/api`, and `uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/app`.

The backend's object-storage contract currently has a secure local development implementation. Configure it with `STORAGE_BACKEND=local` and `LOCAL_STORAGE_ROOT=../../storage`; relative roots resolve from this `apps/api` directory. The implementation is not an upload API and local files are not durable production storage.
