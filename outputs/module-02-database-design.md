# Module 2: Database Design

## Entity relationships

```text
users 1 ─── * build_logs 1 ─── 1 analyses
                                 * ─── 0..1 incident_patterns
```

- A `user` owns uploaded `build_logs`.
- Each log has one analysis record. It begins as `PENDING` and is updated to `COMPLETED` or `FAILED`.
- An analysis may point to a shared `incident_pattern`: a normalized, reusable record for recurring failures. This makes history search useful without requiring embeddings or a vector database.

## Table purpose

| Table | Why it exists |
|---|---|
| `users` | Stores a developer's account and BCrypt password hash. Email is globally unique. |
| `build_logs` | Stores the submitted text log, its source, upload state, original file name, and SHA-256 checksum. |
| `analyses` | Stores the AI/rule-engine result separately from source data so an analysis can fail or be retried without losing the upload. |
| `incident_patterns` | Stores canonical recurring-failure data: category, fingerprint, root cause, suggested fixes, and occurrence count. |

## Important design choices

- UUID primary keys avoid predictable identifiers in public APIs.
- `TIMESTAMPTZ` records time safely across developer machines and deployment regions.
- JSONB stores variable-length extracted error snippets and fixes without creating unnecessary child tables.
- A unique `build_log_id` in `analyses` enforces one current analysis per upload for the MVP.
- Foreign-key cascades remove a user's logs and analyses when an account is deliberately deleted. An incident pattern remains reusable; its link is set to null if the pattern is removed.
- Check constraints prevent invalid enum-like values even when data is inserted outside Spring Boot.
- Indexes cover the expected screens: upload history, dashboard category counts, and incident search.

## How similarity works in the MVP

The AI service creates a stable `fingerprint`, for example from the normalized error category plus the key exception or missing dependency. Spring Boot finds the same fingerprint in `incident_patterns`; on a match, it increments `occurrence_count` and links the analysis. This is explainable and lightweight. Semantic/vector similarity is a sensible future enhancement, but not needed for a 10–15 day project.

## Flyway placement

Copy `V1__initial_schema.sql` into:

`backend/src/main/resources/db/migration/V1__initial_schema.sql`

When Spring Boot starts with Flyway enabled, it will create the schema automatically.
