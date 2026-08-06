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

The local products table supports repository development, but there are no product API routes or frontend product workflows. Future API routes must call services, services must depend on repository interfaces, and only DynamoDB infrastructure code may call Boto3.
