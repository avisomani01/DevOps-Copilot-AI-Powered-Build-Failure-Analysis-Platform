# Module 11: Docker

Docker packaging is included for the React frontend, Spring Boot backend, FastAPI service, and PostgreSQL database.

## Files added

| File | Purpose |
|---|---|
| `backend/Dockerfile` | Multi-stage Maven build and a small Java 21 runtime image running as a non-root user. |
| `ai-service/Dockerfile` | Python 3.12 FastAPI image running as a non-root user. |
| `frontend/Dockerfile` | Builds React with Vite, then serves the static output through Nginx. |
| `frontend/nginx.conf` | Serves the React single-page app and reverse-proxies `/api/` to Spring Boot. |
| `docker-compose.yml` | Orchestrates PostgreSQL, FastAPI, Spring Boot, frontend, and optional Ollama. |
| `.env.example` | Safe local-development configuration template. |

## Start the default stack

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000).

The browser calls `/api/v1` on the same origin. Nginx proxies that request to the backend container, so no browser CORS configuration is needed in the Docker environment.

The default AI mode is rule-based. It does not require Ollama and is sufficient for a reliable project demonstration.

## Optional Ollama enrichment

1. In `.env`, set `OLLAMA_ENABLED=true`.
2. Start the Ollama profile:

```powershell
docker compose --profile ollama up --build -d
```

3. Download the configured model once:

```powershell
docker compose exec ollama ollama pull llama3.2:3b
```

FastAPI automatically falls back to rules if Ollama or the model is unavailable.

## Useful commands

```powershell
docker compose ps
docker compose logs -f backend
docker compose down
```

`docker compose down` stops the project but retains PostgreSQL data in the named Docker volume. To intentionally remove local database data as well, run `docker compose down -v`.

## Configuration note

The `.env.example` credentials and JWT key are only local-development defaults. Before a public deployment, create a strong, unique PostgreSQL password and a unique base64-encoded JWT key of at least 32 random bytes. Keep the real `.env` file out of Git.

## Verification

The required Docker files and service topology were created. Docker CLI is not installed in this workspace, so `docker compose config`, image builds, and container smoke tests must be run on a machine with Docker Desktop installed.
