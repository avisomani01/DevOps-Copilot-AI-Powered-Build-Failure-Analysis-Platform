r"""One-command local launcher for DevOps Copilot Lite.

Run with: .\ai-service\.venv\Scripts\python.exe app.py
Stop every service with Ctrl+C.
"""

from __future__ import annotations

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
VENV_PYTHON = AI_SERVICE / ".venv" / "Scripts" / "python.exe"


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


def postgres_is_running() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(1)
        return connection.connect_ex(("127.0.0.1", 5432)) == 0


def validate_prerequisites() -> None:
    if not VENV_PYTHON.is_file():
        raise RuntimeError(
            "Python virtual environment is missing. Run '.\\setup.ps1' from the ai-service folder first."
        )
    require_command("java", "Install a Java 25 JDK.")
    require_command("mvn", "Install Apache Maven and reopen PowerShell.")
    require_command("node", "Install Node.js LTS and reopen PowerShell.")
    require_command("npm", "Install Node.js LTS and reopen PowerShell.")
    if not postgres_is_running():
        raise RuntimeError("PostgreSQL is not running on localhost:5432. Start the PostgreSQL Windows service first.")


def main() -> int:
    try:
        validate_prerequisites()
    except RuntimeError as error:
        print(f"Cannot start DevOps Copilot: {error}", file=sys.stderr)
        return 1

    services = [
        Service("Python AI service", [str(VENV_PYTHON), "-m", "uvicorn", "app.main:app", "--port", "8000"], AI_SERVICE),
        Service("Spring backend", ["mvn.cmd", "spring-boot:run"], BACKEND),
        Service("React frontend", ["npm.cmd", "run", "dev", "--", "--host", "127.0.0.1"], FRONTEND),
    ]

    try:
        for service in services:
            service.start()
        print("\nDevOps Copilot is starting. Open http://localhost:5173 when Vite is ready.")
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
