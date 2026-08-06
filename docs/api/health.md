# Health API

`GET /api/v1/health` is a liveness probe and has no dependency checks.

`GET /api/v1/health/ready` validates loaded settings during application startup and performs a bounded DynamoDB `ListTables` request. It returns HTTP 503 with a generic dependency status if DynamoDB is unavailable.
