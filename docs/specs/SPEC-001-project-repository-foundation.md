# SPEC-001: Project Repository Foundation

## Status

Implemented

## Objective

Create a runnable, testable monorepo foundation for CatalogIQ AI using a React JavaScript frontend, a Python 3.12 FastAPI backend, and DynamoDB Local. The foundation must remain deployment-aware without provisioning product data or AWS infrastructure.

## Requirements

1. Use React, JavaScript, Vite, Material UI, React Router, TanStack Query, React Hook Form, Zod, Axios, Vitest, and React Testing Library on the frontend.
2. Use FastAPI, Pydantic v2, Pydantic Settings, Boto3, Mangum, pytest, Ruff, and mypy on the backend.
3. Run only DynamoDB Local in Docker Compose, on host port 8001, with persistent shared storage.
4. Select local or AWS DynamoDB through `DYNAMODB_ENDPOINT_URL`; never hardcode future application table names.
5. Provide exact liveness and readiness contracts under `/api/v1/health`.
6. Provide a Material UI application shell, environment examples, local setup instructions, serverless architecture documentation, and checks for both applications.

## Acceptance Criteria

- `GET /api/v1/health` returns the specified status, service, and version.
- `GET /api/v1/health/ready` returns ready only after a bounded DynamoDB connectivity check.
- Readiness failures return 503 without endpoint details, credentials, table content, or stack traces.
- Blank `DYNAMODB_ENDPOINT_URL` causes Boto3 to use its normal AWS endpoint and credential chain.
- The Lambda handler wraps the same FastAPI application using Mangum.
- Backend tests, lint, formatting, strict mypy, frontend tests, lint, formatting, production build, and Compose validation pass.
- The repository contains no TypeScript, PostgreSQL, SQLAlchemy, Alembic, product tables, or product features.

## Explicit Exclusions

Product schemas and tables, CRUD, PDF processing, S3 resources, file uploads, AI extraction, validation, review flows, dashboards, authentication, real AWS resources, deployment, and CI/CD deployment are not part of this specification.
