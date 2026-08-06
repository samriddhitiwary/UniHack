# Security

Do not report security vulnerabilities in public issues. Send a private report to the repository owner with reproduction steps, affected versions, and impact.

Never commit AWS credentials, AI provider keys, customer documents, or `.env` files. Frontend environment variables are public by design and must never contain secrets. Local DynamoDB dummy credentials are generated in backend client configuration only for the explicitly configured local endpoint.
