# DevOps Copilot Lite

## One-command local start (without Docker)

Install PostgreSQL, Node.js LTS, Java 25 JDK, and Apache Maven first. Ensure
the PostgreSQL service is running and that the `devops_copilot` database and
`devops_user` user have been created. Then, from the project root, run:

```powershell
.\ai-service\.venv\Scripts\python.exe app.py
```

`app.py` validates the required tools, confirms PostgreSQL is available, then
starts the Python AI service, Spring backend, and React frontend in one terminal.
Open http://localhost:5173 after the frontend starts, and press `Ctrl+C` to stop
all services. The first time, run `npm install` inside `frontend/`.
