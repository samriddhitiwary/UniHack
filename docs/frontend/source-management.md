# Source Management

Sources use `GET /products/{productId}/sources` newest-first with opaque cursor Load More. Counts are described as loaded when another page exists; no global total is invented.

The accessible dropzone and native picker upload one file at a time. Supported client pairs are PDF (`application/pdf`), CSV (`text/csv`, `application/csv`, or `application/vnd.ms-excel`), PNG, JPEG, and WEBP. PDF/images are rejected above 10 MiB and CSV above 5 MiB. The backend remains authoritative for MIME, signature, content, and size validation. Upload progress is indeterminate because the current transport does not expose reliable percentages.

Text creation uses an optional 200-character display name and required trimmed content up to 50,000 characters. Neither upload nor text creation starts a workflow. Both invalidate the Product source list and retain the rest of the workspace after failure.

Source rows show friendly type/status, created date, bounded failures, and no storage keys. Rename is omitted. Delete uses a focused confirmation and the retrieved positive source version. Deletion is disabled while a workflow is RUNNING or WAITING_FOR_REVIEW. A source added during those states is included only in a future workflow.
