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

The frontend owns presentation and browser-side state. The API owns validated configuration and future application behavior. The product domain model is independent of Boto3. Its repository protocol returns domain entities, while the DynamoDB implementation owns item naming, serialization, conditional writes, index queries, and cursors.

The local products table supports repository development. SPEC-005 exposes create, list, retrieve, and partial-update routes through this dependency chain:

```text
Product route -> ProductService -> ProductRepository protocol -> DynamoDBProductRepository
```

FastAPI providers construct the configured repository and service, so tests can replace the service without AWS. Routes never import Boto3 or instantiate repositories. The list service selects the existing creation-time or status access pattern, while cursor decoding and newest-first DynamoDB queries remain repository responsibilities. For PATCH, the service retrieves the immutable entity and merges only explicitly supplied editable fields; the repository owns conditional version comparison, version increment, and update timestamp. There is no product deletion, PUT replacement, or frontend product workflow; only DynamoDB infrastructure code may call Boto3.
