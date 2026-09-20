# Module 7: Secure Log Upload

This module adds authenticated log upload and history retrieval. The raw log is stored in PostgreSQL through the existing `build_logs` table; logs are never written to a public filesystem path.

## APIs

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/v1/logs` | Upload one `.txt` build log as multipart form field `file`. Returns `201 Created`. |
| `GET` | `/api/v1/logs?page=0&size=20` | Returns the current user's paginated upload history. |
| `GET` | `/api/v1/logs/{logId}` | Returns metadata for a log only when it belongs to the current user. |

All three require `Authorization: Bearer <accessToken>`.

Example upload:

```powershell
curl.exe -X POST http://localhost:8080/api/v1/logs `
  -H "Authorization: Bearer <accessToken>" `
  -F "file=@C:\logs\maven-failure.txt;type=text/plain"
```

## Validation and safety controls

- Only non-empty `.txt` files are accepted.
- Spring Boot rejects multipart requests above 2 MB, and the service checks the same limit before reading content.
- Content must decode as UTF-8 and cannot contain a null byte.
- The original name is cleaned and reduced to its basename, avoiding path traversal or server-side file writes.
- A SHA-256 checksum is stored for each upload; it supports later duplicate detection and incident fingerprinting.
- `source_type` is detected from stable log markers (Maven, Gradle, Java, Python, Docker, Jenkins, or generic).
- Every read uses `findByIdAndUserId` or `findByUserId`, enforcing ownership in the data query rather than relying only on the UI.
- File content is deliberately absent from list and detail responses. This prevents accidental large-response or sensitive-log exposure; the analysis service will receive it internally in Module 8.

## Frontend integration

The upload page validates extension and size before requesting the API, displays server errors, and redirects to history only after a successful `201` response. The history page now loads the authenticated user’s actual uploaded logs instead of demo data.

## Verification

The upload controller, service, ownership repository query, multipart limits, and React API integration were statically checked. The Maven and Vite lifecycles remain pending because their package dependencies have not been installed in this workspace.
