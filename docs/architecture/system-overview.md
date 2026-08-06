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

The local products table supports repository development. SPEC-003 exposes only create and retrieve routes through this dependency chain:

```text
Product route -> ProductService -> ProductRepository protocol -> DynamoDBProductRepository
```

FastAPI providers construct the configured repository and service, so tests can replace the service without AWS. Routes never import Boto3 or instantiate repositories. There are no product list/update/delete routes or frontend product workflows; only DynamoDB infrastructure code may call Boto3.
