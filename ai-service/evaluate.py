"""Evaluate the deterministic rule engine against a labelled JSONL dataset."""

import argparse
import json
from collections import Counter
from pathlib import Path

from app.services.rule_engine import analyze_with_rules


def load_cases(dataset_path: Path) -> list[dict[str, str]]:
    cases = []
    for line_number, line in enumerate(dataset_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        case = json.loads(line)
        if not isinstance(case.get("expected_category"), str) or not isinstance(case.get("log_content"), str):
            raise ValueError(f"Invalid case at line {line_number}: expected_category and log_content are required strings")
        cases.append(case)
    if not cases:
        raise ValueError("Dataset has no cases")
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate rule-engine category accuracy.")
    parser.add_argument("--dataset", type=Path, default=Path("datasets/evaluation_cases.jsonl"))
    args = parser.parse_args()

    cases = load_cases(args.dataset)
    correct = 0
    confusion = Counter()
    mistakes = []

    for index, case in enumerate(cases, start=1):
        predicted = analyze_with_rules(case["log_content"])["error_category"]
        expected = case["expected_category"]
        confusion[(expected, predicted)] += 1
        if predicted == expected:
            correct += 1
        else:
            mistakes.append({"case": index, "expected": expected, "predicted": predicted})

    accuracy = correct / len(cases) * 100
    print(f"Cases: {len(cases)}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {accuracy:.2f}%")
    print("\nConfusion matrix (expected -> predicted):")
    for (expected, predicted), count in sorted(confusion.items()):
        print(f"  {expected} -> {predicted}: {count}")
    if mistakes:
        print("\nMisclassifications:")
        for mistake in mistakes:
            print(f"  Case {mistake['case']}: expected {mistake['expected']}, got {mistake['predicted']}")


if __name__ == "__main__":
    main()
