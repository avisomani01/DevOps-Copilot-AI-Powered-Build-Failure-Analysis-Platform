"""Train the optional local classifier from anonymized labelled JSONL logs."""

import argparse
from collections import Counter
from pathlib import Path

from evaluate import load_cases
from app.services.rule_engine import RULES


MINIMUM_CASES = 100
MINIMUM_PER_CATEGORY = 8


def build_pipeline(calibration_folds: int):
    """Same pipeline diagnose_model.py uses, so its numbers describe the model this
    script actually saves. LogisticRegression's raw predict_proba on a 9-class problem
    under-states confidence even when the top prediction is correct (see evaluate_ml.py) -
    CalibratedClassifierCV fixes that by learning an actual probability-to-confidence
    mapping via cross-validation, instead of trusting the raw softmax output."""
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    base_classifier = LogisticRegression(max_iter=2_000, class_weight="balanced", random_state=42)
    return Pipeline([
        ("features", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True)),
        ("classifier", CalibratedClassifierCV(estimator=base_classifier, method="sigmoid", cv=calibration_folds)),
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="Train DevOps Copilot's optional local log classifier.")
    parser.add_argument("--dataset", type=Path, default=Path("datasets/training_cases.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("models/log_classifier.joblib"))
    parser.add_argument("--calibration-folds", type=int, default=3, help="CV folds used to calibrate confidence scores.")
    parser.add_argument("--allow-small-dataset", action="store_true", help="For development only; never use this model for accuracy claims.")
    args = parser.parse_args()

    try:
        from joblib import dump
        from sklearn.model_selection import train_test_split
    except ImportError as error:
        raise SystemExit("Install dependencies first: pip install -r requirements.txt") from error

    cases = load_cases(args.dataset)
    distribution = Counter(case["expected_category"] for case in cases)
    supported_categories = {rule.category for rule in RULES} | {"UNKNOWN"}
    unsupported = sorted(set(distribution) - supported_categories)
    if unsupported:
        raise SystemExit(f"Unsupported categories: {', '.join(unsupported)}")
    if not args.allow_small_dataset and (len(cases) < MINIMUM_CASES or min(distribution.values()) < MINIMUM_PER_CATEGORY):
        raise SystemExit(
            f"Need at least {MINIMUM_CASES} cases and {MINIMUM_PER_CATEGORY} per category. "
            f"Current dataset: {len(cases)} cases; {dict(sorted(distribution.items()))}."
        )
    calibration_folds = min(args.calibration_folds, min(distribution.values()))
    if calibration_folds < 2:
        raise SystemExit(
            "Every category needs at least 2 examples to calibrate confidence. "
            f"Smallest category currently has {min(distribution.values())}."
        )

    X = [case["log_content"] for case in cases]
    y = [case["expected_category"] for case in cases]

    # Quick train/test sanity check before committing to the full fit below. This does not
    # replace diagnose_model.py (run that first) - it is a last-mile guard against saving an
    # obviously broken model when someone skips straight to train_model.py.
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
        sanity_model = build_pipeline(calibration_folds)
        sanity_model.fit(X_train, y_train)
        train_acc = sanity_model.score(X_train, y_train)
        test_acc = sanity_model.score(X_test, y_test)
        print(f"Sanity check - train accuracy: {train_acc:.1%}, held-out test accuracy: {test_acc:.1%}")
        if train_acc - test_acc > 0.25:
            print(
                f"[!] Warning: {train_acc - test_acc:.0%} gap between train and test accuracy. "
                "This looks like overfitting - consider running diagnose_model.py before trusting "
                "this model. Continuing to save anyway since this is only a warning."
            )
    except ValueError as error:
        print(f"Skipped train/test sanity check: {error}")

    model = build_pipeline(calibration_folds)
    model.fit(X, y)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    dump(model, args.output)
    print(f"Saved model: {args.output}")
    print(f"Training cases: {len(cases)}")
    print(f"Categories: {dict(sorted(distribution.items()))}")
    print("Use evaluate_ml.py against datasets/evaluation_cases.jsonl before enabling ML_ENABLED=true.")


if __name__ == "__main__":
    main()

