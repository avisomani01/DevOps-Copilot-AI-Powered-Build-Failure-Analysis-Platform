"""Run DevOps Copilot Lite's rule-based analyzer without FastAPI or Docker."""

import argparse
import json
from pathlib import Path

from app.services.rule_engine import analyze_with_rules


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a UTF-8 build log with DevOps Copilot Lite rules.")
    parser.add_argument("log_file", type=Path, help="Path to a UTF-8 .txt build log")
    parser.add_argument(
        "--source-type",
        default="GENERIC",
        choices=("MAVEN", "GRADLE", "JAVA", "PYTHON", "DOCKER", "JENKINS", "GENERIC"),
        help="Build system that produced the log; resolves otherwise ambiguous errors.",
    )
    args = parser.parse_args()

    try:
        content = args.log_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        parser.error(f"File not found: {args.log_file}")
    except UnicodeDecodeError:
        parser.error("Log file must be UTF-8 text")

    if not content.strip():
        parser.error("Log file is empty")

    print(json.dumps(analyze_with_rules(content, args.source_type), indent=2))


if __name__ == "__main__":
    main()
