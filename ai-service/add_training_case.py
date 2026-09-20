"""Append a real, labelled log/error to datasets/training_cases.jsonl without hand-writing JSON.

This is the "how" for building a real dataset: paste in an actual failure you found in your
CI history, tell it which category it belongs to, and it appends a properly formatted line
and shows you the running per-category counts so you know what still needs more examples.

Usage examples:

    # From a file you saved (e.g. a downloaded Jenkins/GitHub Actions log excerpt)
    python add_training_case.py --category PYTHON_MODULE --file path/to/snippet.log

    # Paste text directly
    python add_training_case.py --category DOCKER_BUILD --text "failed to solve: ..."

    # No --category/--file/--text: interactive mode: paste the log, blank line to end,
    # then pick a category from a numbered list.
    python add_training_case.py

Categories are restricted to what the app actually supports: the rule engine's categories,
plus UNKNOWN for real failures that genuinely don't fit any of them (those are useful too -
they teach the model to correctly abstain instead of guessing).
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from app.services.rule_engine import RULES

CATEGORIES = [rule.category for rule in RULES] + ["UNKNOWN"]
DATASET_PATH = Path("datasets/training_cases.jsonl")


def load_existing(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            cases.append(json.loads(line))
    return cases


def prompt_for_text() -> str:
    print("Paste the log/error content. Enter a blank line when done:")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "":
            break
        lines.append(line)
    return "\n".join(lines)


def prompt_for_category() -> str:
    print("\nWhich category does this belong to?")
    for index, category in enumerate(CATEGORIES, start=1):
        print(f"  {index}. {category}")
    while True:
        choice = input("Enter a number: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(CATEGORIES):
            return CATEGORIES[int(choice) - 1]
        print("Not a valid choice, try again.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Append a labelled real case to the training dataset.")
    parser.add_argument("--category", choices=CATEGORIES, help="One of: " + ", ".join(CATEGORIES))
    parser.add_argument("--file", type=Path, help="Read log_content from this file.")
    parser.add_argument("--text", type=str, help="Provide log_content directly on the command line.")
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    args = parser.parse_args()

    if args.file:
        log_content = args.file.read_text(encoding="utf-8").strip()
    elif args.text:
        log_content = args.text.strip()
    else:
        log_content = prompt_for_text().strip()

    if not log_content:
        raise SystemExit("No log content provided - nothing to add.")

    category = args.category or prompt_for_category()

    existing = load_existing(args.dataset)
    if any(case["log_content"] == log_content for case in existing):
        print("\n[!] This exact text is already in the dataset - skipping duplicate.")
        sys.exit(0)

    new_case = {"expected_category": category, "log_content": log_content}
    args.dataset.parent.mkdir(parents=True, exist_ok=True)
    with args.dataset.open("a", encoding="utf-8") as f:
        f.write(json.dumps(new_case) + "\n")

    existing.append(new_case)
    counts = Counter(case["expected_category"] for case in existing)
    print(f"\nAdded 1 case to {args.dataset} (category: {category}).")
    print(f"Dataset now has {len(existing)} cases:")
    for cat in CATEGORIES:
        marker = " <- still thin, add more" if counts.get(cat, 0) < 15 else ""
        print(f"  {cat:<20} {counts.get(cat, 0):>3}{marker}")


if __name__ == "__main__":
    main()
