# Module 4: Python AI Service

The FastAPI implementation is in `ai-service/`. It is intentionally independent from Spring Boot: Spring Boot remains responsible for authentication and persistence, while this service only transforms log text into an analysis.

## API contract

`POST /api/v1/analyze`

```json
{
  "log_content": "[ERROR] cannot find symbol",
  "source_type": "MAVEN"
}
```

```json
{
  "error_category": "JAVA_COMPILATION",
  "confidence_score": 90,
  "summary": "Java compilation failed before the build could complete.",
  "root_cause": "The source code references a missing symbol, has incompatible types, or contains a syntax error.",
  "extracted_errors": ["[ERROR] cannot find symbol"],
  "suggested_fixes": ["Read the first compiler error; later errors may be consequences."],
  "fingerprint": "...",
  "analyzer_type": "RULE_BASED",
  "llm_enrichment_applied": false
}
```

`GET /api/v1/health` reports whether the service is available and whether Ollama enrichment is enabled.

## Design choices

- `rule_engine.py` recognizes Maven, Gradle, Java, Python, Docker, Jenkins, test, and configuration errors. It extracts only relevant error lines, which avoids sending a whole log to the LLM.
- Every result has a stable SHA-256 fingerprint. Spring Boot will use it in Module 8 to find or update a matching `incident_pattern`.
- `OllamaClient` is optional and has a strict timeout. It may improve the plain-language summary and fixes, but it never changes category, confidence, extracted errors, or fingerprint.
- If Ollama is off, slow, unavailable, or returns invalid JSON, the rule result is returned without failing the request.
- Pydantic limits uploaded analysis text to 2 MB at the service boundary. Spring Boot will enforce the same upload policy.

## Run it

```powershell
cd ai-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

For optional local-model enrichment, install and start Ollama, pull a small model such as `llama3.2:3b`, and set `OLLAMA_ENABLED=true`. The `.env.example` file documents all options.

## Verification

`tests/test_rule_engine.py` passed three cases: Java compilation, missing Python module, and unknown-log fallback. Python syntax compilation passed for the service. The available bundled Python runtime does not contain FastAPI, so live endpoint startup requires installing `requirements.txt` in a virtual environment.
