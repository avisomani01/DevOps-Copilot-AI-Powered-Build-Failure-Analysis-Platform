"""Diagnose the optional ML classifier for overfitting / underfitting BEFORE saving a model.

train_model.py fits on 100% of the dataset and saves whatever comes out — there is no
train/test split, no cross-validation, and evaluate.py only scores the deterministic rule
engine, never the ML model. That means today there is no way to know, before shipping a
model, whether it actually generalizes or just memorized the training log lines.

Run this BEFORE train_model.py:

    python diagnose_model.py --dataset datasets/training_cases.jsonl

It does not save anything. It fits the same pipeline train_model.py uses, on a held-out
split and via cross-validation, and prints the numbers you need to tell overfitting apart
from underfitting apart from "dataset is just too small to trust yet".
"""

import argparse
from collections import Counter
from pathlib import Path

from evaluate import load_cases


def build_pipeline(calibration_folds: int = 3):
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
    parser = argparse.ArgumentParser(description="Diagnose bias/variance behaviour before training a final model.")
    parser.add_argument("--dataset", type=Path, default=Path("datasets/training_cases.jsonl"))
    parser.add_argument("--folds", type=int, default=5, help="Cross-validation folds (capped to the smallest category).")
    parser.add_argument("--test-size", type=float, default=0.2, help="Fraction held out for the train/test gap check.")
    args = parser.parse_args()

    try:
        import numpy as np
        from sklearn.metrics import classification_report, confusion_matrix
        from sklearn.model_selection import StratifiedKFold, cross_val_score, learning_curve, train_test_split
    except ImportError as error:
        raise SystemExit("Install dependencies first: pip install -r requirements.txt") from error

    cases = load_cases(args.dataset)
    X = [case["log_content"] for case in cases]
    y = [case["expected_category"] for case in cases]

    distribution = Counter(y)
    print(f"Total cases: {len(cases)}")
    print(f"Categories ({len(distribution)}): {dict(sorted(distribution.items()))}")
    smallest_class = min(distribution.values())
    folds = min(args.folds, smallest_class)
    calibration_folds = min(3, folds)
    if smallest_class < args.folds:
        print(f"\n[!] Smallest category has only {smallest_class} example(s) - below --folds={args.folds}.")
        print(f"    Using {folds}-fold CV instead. Numbers below will still be noisy until every")
        print("    category has more labelled examples.")

    # 1) Train/test gap - the single most direct overfitting signal.
    print("\n--- Train vs. held-out test accuracy ---")
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=args.test_size, stratify=y, random_state=42
        )
    except ValueError as error:
        raise SystemExit(
            f"Could not create a stratified split: {error}\n"
            "Every category needs at least 2 examples to split. Add more labelled data first."
        )

    pipeline = build_pipeline(calibration_folds)
    pipeline.fit(X_train, y_train)
    train_acc = pipeline.score(X_train, y_train)
    test_acc = pipeline.score(X_test, y_test)
    gap = train_acc - test_acc
    print(f"Train accuracy: {train_acc:.1%}  ({len(X_train)} examples)")
    print(f"Test accuracy:  {test_acc:.1%}  ({len(X_test)} examples)")
    print(f"Gap:            {gap:+.1%}")

    # 2) Cross-validated accuracy - more stable than one split; its spread shows how much
    #    the result depends on which examples happen to land in the split.
    print(f"\n--- {folds}-fold cross-validation (whole dataset) ---")
    cv_scores = None
    try:
        skf = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
        cv_scores = cross_val_score(build_pipeline(calibration_folds), X, y, cv=skf)
        print(f"Scores: {[f'{s:.1%}' for s in cv_scores]}")
        print(f"Mean:   {cv_scores.mean():.1%}")
        print(f"Std:    {cv_scores.std():.1%}")
    except ValueError as error:
        print(f"Skipped: {error}")

    # 3) Per-category precision/recall on the held-out test set - this is where
    #    a specific category doing badly shows up, even when overall accuracy looks fine.
    print("\n--- Classification report (held-out test set) ---")
    predictions = pipeline.predict(X_test)
    print(classification_report(y_test, predictions, zero_division=0))

    labels = sorted(distribution)
    matrix = confusion_matrix(y_test, predictions, labels=labels)
    print("--- Confusion matrix (rows = expected, columns = predicted) ---")
    header = "".join(f"{label[:10]:>12}" for label in labels)
    print(f"{'':>22}{header}")
    for label, row in zip(labels, matrix):
        row_text = "".join(f"{value:>12}" for value in row)
        print(f"{label:>22}{row_text}")

    # 4) Learning curve - does more data actually help? This is what separates "needs more
    #    data" (high variance) from "needs a better model/features" (high bias).
    print("\n--- Learning curve (accuracy vs. training-set size) ---")
    train_scores = val_scores = None
    try:
        import warnings

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            train_sizes, train_scores, val_scores = learning_curve(
                build_pipeline(calibration_folds), X, y, cv=folds,
                train_sizes=np.linspace(0.3, 1.0, 5), random_state=42, error_score=np.nan,
            )
        for size, tr, va in zip(train_sizes, train_scores.mean(axis=1), val_scores.mean(axis=1)):
            if np.isnan(tr) or np.isnan(va):
                print(f"  n={int(size):>4}  skipped - too few examples of some category at this size")
            else:
                print(f"  n={int(size):>4}  train={tr:.1%}  val={va:.1%}  gap={tr - va:+.1%}")
    except ValueError as error:
        print(f"Skipped: {error}")

    # 5) Plain-language diagnosis.
    print("\n--- Diagnosis ---")
    diagnosed = False
    if gap > 0.20:
        diagnosed = True
        print(
            f"[!] Likely OVERFITTING: train accuracy ({train_acc:.0%}) is far above test accuracy "
            f"({test_acc:.0%}). Char 3-5-gram TF-IDF with min_df=1 creates a huge, sparse feature "
            "space relative to a small dataset, so the model can memorize training lines instead of "
            "learning general patterns. Try: more examples per category, min_df=2 or 3, a smaller "
            "ngram_range, or a lower C in LogisticRegression."
        )
    if train_acc < 0.65 and test_acc < 0.65:
        diagnosed = True
        print(
            f"[!] Likely UNDERFITTING: even train accuracy ({train_acc:.0%}) is low, so the model "
            "isn't capturing the pattern at all - this usually isn't fixed by adding more data. "
            "Check for mislabeled cases, categories that genuinely overlap in wording, or add "
            "word-level n-grams alongside the char n-grams."
        )
    if cv_scores is not None and cv_scores.std() > 0.15:
        diagnosed = True
        print(
            f"[!] HIGH VARIANCE across folds (std={cv_scores.std():.0%}): accuracy depends heavily "
            "on which examples land in each fold - a strong sign the dataset is still too small to "
            "trust any single accuracy number."
        )
    zero_recall = [labels[i] for i in range(len(labels)) if matrix[i].sum() > 0 and matrix[i][i] == 0]
    if zero_recall:
        diagnosed = True
        print(
            f"[!] The model never correctly predicts: {', '.join(zero_recall)}. Check whether these "
            "categories have too few examples, or overlap heavily in wording with a category the "
            "model prefers instead."
        )
    if not diagnosed:
        print("No major red flags at this dataset size. Re-check as the dataset grows - small")
        print("datasets can look healthy by chance.")

    print("\nThis script never saves a model. Once these numbers look stable and the train/test")
    print("gap is small, run train_model.py to fit on the full dataset and save the artifact.")


if __name__ == "__main__":
    main()
