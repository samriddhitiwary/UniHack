# AWS Serverless Architecture

## Deployment target

```text
AWS Amplify Hosting
        |
        v
Amazon API Gateway -> AWS Lambda (FastAPI + Mangum)
                              |
                     +--------+--------+
                     v                 v
              Amazon DynamoDB     Amazon S3

Logs: Amazon CloudWatch
Secrets: AWS Systems Manager Parameter Store or Secrets Manager
```

SPEC-001 provides only deployment-compatible code and configuration. It does not provision or deploy these resources.

The FastAPI application is stateless and exposed through `app.lambda_handler.handler`. It writes logs to standard output, keeps the DynamoDB client reusable outside route handlers, and uses the standard AWS endpoint when `DYNAMODB_ENDPOINT_URL` is absent. The frontend reads its API base URL from `VITE_API_BASE_URL` and contains no secrets.

The target avoids RDS, App Runner, EC2, NAT Gateway, load balancers, containers in production, and other always-on services. Later deployment specifications must define least-privilege IAM, log retention, billing alerts, tags, package size, and smoke tests.
