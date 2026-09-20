# Module 10: Testing

This project now has focused automated tests for the highest-risk logic in each service. The goal is credible coverage for a college project, not a large enterprise test suite.

## Spring Boot tests

| Test class | What it verifies |
|---|---|
| `JwtServiceTest` | A generated token returns the expected subject; a tampered token is rejected. |
| `AuthenticationServiceTest` | Duplicate email registration is rejected; a new email can be normalized and registered. |
| `BuildLogServiceTest` | Non-`.txt` uploads are rejected; a valid Maven log is stored with detected source type and upload status. |

Spring Boot test support now includes `spring-security-test` for future controller/security integration tests.

Run from `backend/`:

```powershell
mvn test
```

## FastAPI tests

| Test file | What it verifies |
|---|---|
| `test_rule_engine.py` | Java compile, missing Python module, and unknown-log fallback classifications. |
| `test_api.py` | `POST /api/v1/analyze` returns rule-based output when Ollama is disabled and rejects an empty log. |

Run from `ai-service/` after installing requirements:

```powershell
python -m unittest discover -s tests -v
```

The rule-engine subset passed locally: 3 tests passed. The endpoint tests require FastAPI to be installed from `requirements.txt`.

## React tests

Vitest and React Testing Library are configured. `StatusBadge.test.tsx` confirms that a user-facing upload status renders correctly.

Run from `frontend/`:

```powershell
pnpm install
pnpm test
pnpm build
```

## Manual integration checklist

Before a demo, run the three services and verify:

1. Register a new user, log in, and confirm a protected API fails without the JWT.
2. Upload a valid `.txt` Maven failure and confirm that it appears in history.
3. Confirm the analysis shows a summary and fixes when FastAPI is running in rule-based mode.
4. Stop FastAPI and confirm the application records a clear failed-analysis status instead of crashing.
5. Upload the same kind of failure twice and verify that the incident recurrence count increases.
6. Confirm dashboard totals and category bars change after each completed analysis.

## Why this level of testing is appropriate

The suite tests security-sensitive token behavior, input validation, service rules, API contracts, and one frontend component. It is small enough to write and explain within the 10–15 day scope, yet it demonstrates the test pyramid: many fast unit tests, a few API tests, and a short end-to-end manual smoke checklist.
