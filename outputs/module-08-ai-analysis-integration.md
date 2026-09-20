# Module 8: AI Analysis Integration

Spring Boot now invokes the FastAPI AI service after a user uploads a build log, stores the outcome, and exposes it to the React UI.

## APIs

| Method | Route | Result |
|---|---|---|
| `POST` | `/api/v1/logs/{logId}/analysis` | Runs analysis once for an owned uploaded log and returns its stored result. Repeated calls return the existing result. |
| `GET` | `/api/v1/logs/{logId}/analysis` | Retrieves an existing result for an owned log. |

Both routes require a JWT and use the same ownership constraint as the upload APIs.

## Processing flow

```text
React upload
    -> Spring Boot stores validated log
    -> Spring Boot POSTs { log_content, source_type } to FastAPI
    -> FastAPI rules, optionally Ollama enrichment
    -> Spring Boot stores analysis + incident fingerprint
    -> React displays explanation, fixes, confidence, and recurrence count
```

## Incident handling

The FastAPI service provides a stable fingerprint derived from the normalized error. Spring Boot finds an existing `incident_patterns` row for that fingerprint or creates one. On a match, it increments `occurrence_count`; the analysis response then includes `incidentOccurrenceCount` so the UI can indicate recurring failures.

No raw log content is copied into the incident record. The shared incident stores only the category, concise title, root cause, recommended fixes, and recurrence metadata.

## Failure behavior

If FastAPI is unreachable, times out, returns invalid data, or has an internal error, Spring Boot records the analysis as `FAILED`, sets the log status to `FAILED`, and returns a safe explanation. The user sees an “Analysis unavailable” page rather than an unhandled server error. When FastAPI runs normally but Ollama is unavailable, FastAPI itself returns a successful `RULE_BASED` analysis.

## Frontend behavior

The upload page now uploads and starts analysis as one user action. The analysis page loads its real backend result, renders the AI/rule-generated summary and fixes, and distinguishes a failed AI-service request from a completed analysis.

## Verification

Static checks verified the Spring Boot analysis controller/service/DTOs, FastAPI request field names (`log_content`, `source_type`), persistent status transitions, and React API integration. Running the complete integration test needs PostgreSQL, FastAPI dependencies, and Maven installed locally.
