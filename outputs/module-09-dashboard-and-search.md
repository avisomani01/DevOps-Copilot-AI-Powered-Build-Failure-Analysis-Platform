# Module 9: Dashboard and Incident Search

The dashboard and similarity search now use real PostgreSQL data rather than frontend demo values.

## Dashboard API

`GET /api/v1/dashboard`

Example response:

```json
{
  "totalUploads": 12,
  "successfulAnalyses": 10,
  "failedAnalyses": 1,
  "commonCategories": [
    { "category": "MAVEN_DEPENDENCY", "count": 4 },
    { "category": "JAVA_COMPILATION", "count": 3 }
  ]
}
```

The query scopes every count to the authenticated user. It contains total uploads, successful and failed analyses, and category aggregation ordered from most to least common.

## Incident search API

`GET /api/v1/incidents?category=MAVEN_DEPENDENCY&page=0&size=20`

The `category` parameter is optional. Valid values are the project’s `ErrorCategory` values such as `MAVEN_DEPENDENCY`, `JAVA_COMPILATION`, and `DOCKER_BUILD`. The endpoint returns only completed analyses belonging to the authenticated user, including file name, summary, root cause, incident recurrence count, and timestamp.

This preserves log privacy: a developer never sees another account’s log or analysis through the incident search feature.

## Frontend changes

- The dashboard requests its statistics from `/dashboard`, calculates bar widths from the highest category count, and handles empty accounts gracefully.
- The analysis page searches prior completed analyses in the current category and links to matching logs from the same user’s history.
- The recurrence count remains available in the analysis detail sidebar, representing the shared normalized incident-pattern count.

## Why both recurrence count and history search exist

The recurrence count answers “how often has this normalized error occurred?” across stored incident patterns. The history list answers “which of my previous uploads had this category?” They are deliberately separate: the former is an operational signal; the latter is a safe, user-owned troubleshooting trail.

## Verification

Static checks covered controller/service/repository presence, aggregated category queries, authenticated-user scoping, and React dashboard/search API wiring. Full integration testing requires the local PostgreSQL, FastAPI, Maven, and frontend dependency setup described in the earlier module notes.
