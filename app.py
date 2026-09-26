r"""One-command local launcher for DevOps Copilot.

This script sets itself up. On a fresh clone with nothing installed yet, just run:

    python app.py

It will, in order: create the ai-service virtual environment if missing, install its
Python dependencies if missing, run 'npm install' in frontend/ if node_modules is
missing, then start the Python AI service and the React frontend together. Every
later run skips whatever's already set up and starts in a few seconds.

This only touches what the app actually uses: the Python AI service and the React
frontend. It never requires or starts the legacy Java Spring Boot + PostgreSQL
backend, since the app's upload/analyze flow talks directly to the Python service on
port 8000 and never calls that backend. If you specifically want the legacy backend
running too, pass --full (this will then also require Java, Maven, and a running
PostgreSQL, and set those up is on you - this script does not automate that part).

Stop everything with Ctrl+C.
"""

from __future__ import annotations

import argparse
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AI_SERVICE = ROOT / "ai-service"
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV_DIR = AI_SERVICE / ".venv"
VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
FRONTEND_NODE_MODULES = FRONTEND / "node_modules"


@dataclass
class Service:
    name: str
    command: list[str]
    directory: Path
    process: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        print(f"Starting {self.name}...")
        self.process = subprocess.Popen(self.command, cwd=self.directory)

    def stop(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()


def require_command(command: str, installation_hint: str) -> None:
    if shutil.which(command) is None:
        raise RuntimeError(f"'{command}' was not found. {installation_hint}")


def run_step(description: str, command: list[str], directory: Path) -> None:
    """Runs a setup command with live output, and turns a failure into a clear error
    instead of a raw traceback."""
    print(f"{description}...")
    result = subprocess.run(command, cwd=directory)
    if result.returncode != 0:
        raise RuntimeError(f"{description} failed (exit code {result.returncode}). See the output above for details.")


def ensure_backend_ready() -> None:
    if not VENV_PYTHON.is_file():
        require_command("python", "Install Python 3.11+ and reopen PowerShell.")
        run_step("Creating Python virtual environment for ai-service", [sys.executable, "-m", "venv", str(VENV_DIR)], AI_SERVICE)
    run_step(
        "Installing/checking Python dependencies (fast if already installed)",
        [str(VENV_PYTHON), "-m", "pip", "install", "-q", "-r", "requirements.txt"], AI_SERVICE,
    )


def ensure_frontend_ready() -> None:
    require_command("node", "Install Node.js LTS from nodejs.org and reopen PowerShell.")
    require_command("npm", "Install Node.js LTS from nodejs.org and reopen PowerShell.")
    if not FRONTEND_NODE_MODULES.is_dir():
        run_step("Installing frontend dependencies (npm install, first time only)", ["npm.cmd", "install"], FRONTEND)


def postgres_is_running() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(1)
        return connection.connect_ex(("127.0.0.1", 5432)) == 0


def validate_legacy_prerequisites() -> None:
    require_command("java", "Install a Java 25 JDK.")
    require_command("mvn", "Install Apache Maven and reopen PowerShell.")
    if not postgres_is_running():
        raise RuntimeError("PostgreSQL is not running on localhost:5432. Start the PostgreSQL Windows service first.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up (if needed) and start DevOps Copilot locally.")
    parser.add_argument(
        "--full", action="store_true",
        help="Also start the legacy Java Spring Boot + PostgreSQL backend (not required for the app to work; not auto-installed).",
    )
    args = parser.parse_args()

    try:
        ensure_backend_ready()
        ensure_frontend_ready()
        if args.full:
            validate_legacy_prerequisites()
    except RuntimeError as error:
        print(f"\nCannot start DevOps Copilot: {error}", file=sys.stderr)
        return 1

    services = [
        Service("Python AI service", [str(VENV_PYTHON), "-m", "uvicorn", "app.main:app", "--port", "8000"], AI_SERVICE),
        Service("React frontend", ["npm.cmd", "run", "dev", "--", "--host", "127.0.0.1"], FRONTEND),
    ]
    if args.full:
        services.insert(1, Service("Spring backend (legacy, --full)", ["mvn.cmd", "spring-boot:run"], BACKEND))

    try:
        for service in services:
            service.start()
        print("\nDevOps Copilot is starting. Open http://localhost:5173 when Vite is ready.")
        if not args.full:
            print("(Legacy Java/PostgreSQL backend not started - it isn't used by the app. Pass --full to include it.)")
        print("Press Ctrl+C to stop all services.\n")
        while True:
            for service in services:
                if service.process and service.process.poll() is not None:
                    raise RuntimeError(f"{service.name} stopped unexpectedly (exit code {service.process.returncode}).")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping services...")
    except RuntimeError as error:
        print(f"\n{error}", file=sys.stderr)
        return 1
    finally:
        for service in reversed(services):
            service.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
