"""Evaluate the SAVED ML classifier against a held-out dataset, and compare it to the rule engine.

evaluate.py only scores the deterministic rule engine - it never touches the ML model, so
there is currently no number anywhere that tells you whether ML_ENABLED=true is a good idea.
This script closes that gap: it runs datasets/evaluation_cases.jsonl (cases the model never
saw during training) through the saved model and reports the number that should actually
decide whether to turn ML on.

Usage:
    python evaluate_ml.py --model models/log_classifier.joblib
"""

import argparse
from pathlib import Path

from evaluate import load_cases
from app.services.rule_engine import analyze_with_rules


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the trained ML classifier on held-out cases.")
    parser.add_argument("--dataset", type=Path, default=Path("datasets/evaluation_cases.jsonl"))
    parser.add_argument("--model", type=Path, default=Path("models/log_classifier.joblib"))
    parser.add_argument("--minimum-confidence", type=float, default=75.0)
    args = parser.parse_args()

    try:
        from joblib import load
    except ImportError as error:
        raise SystemExit("Install dependencies first: pip install -r requirements.txt") from error

    if not args.model.is_file():
        raise SystemExit(f"No model found at {args.model}. Run train_model.py first.")

    model = load(args.model)
    cases = load_cases(args.dataset)

    rule_correct = 0
    ml_correct = 0
    ml_abstained = 0
    ml_raw_correct = 0  # top-1 correct regardless of the confidence threshold
    ml_wrong_when_confident = []
    confidences_when_correct = []

    for case in cases:
        expected = case["expected_category"]
        log_content = case["log_content"]

        if analyze_with_rules(log_content)["error_category"] == expected:
            rule_correct += 1

        probabilities = model.predict_proba([log_content])[0]
        index = probabilities.argmax()
        confidence = float(probabilities[index]) * 100
        ml_prediction = str(model.classes_[index])

        if ml_prediction == expected:
            ml_raw_correct += 1
            confidences_when_correct.append(confidence)

        if confidence < args.minimum_confidence:
            ml_abstained += 1
        elif ml_prediction == expected:
            ml_correct += 1
        else:
            ml_wrong_when_confident.append(
                {"expected": expected, "predicted": ml_prediction, "confidence": confidence}
            )

    total = len(cases)
    print(f"Cases: {total}")
    print(f"Rule engine accuracy:                 {rule_correct / total:.1%}")
    print(f"ML raw top-1 accuracy (no threshold):  {ml_raw_correct / total:.1%}")
    print(f"ML confident-and-correct (>= {args.minimum_confidence:.0f}%):    {ml_correct / total:.1%}")
    print(f"ML abstained (below confidence):       {ml_abstained / total:.1%}")
    print(f"ML confident-and-wrong:                {len(ml_wrong_when_confident) / total:.1%}")
    if confidences_when_correct:
        avg_conf = sum(confidences_when_correct) / len(confidences_when_correct)
        print(f"Avg confidence on CORRECT predictions: {avg_conf:.1f}%")
        if ml_raw_correct > ml_correct:
            print(
                "\n[!] The model's raw top-1 predictions are right more often than the confidence "
                f"threshold lets through ({ml_raw_correct}/{total} correct vs. {ml_correct}/{total} "
                f"actually used). That means ML_MINIMUM_CONFIDENCE={args.minimum_confidence:.0f} is "
                "miscalibrated for this model, not that the model doesn't know the answer. This is a "
                "different problem than overfitting: with 9 classes, a multinomial LogisticRegression "
                "spreads probability mass across plausible categories even when its top pick is "
                "correct, so its confidence rarely reaches a threshold tuned by eye. Fix by lowering "
                "the threshold based on this data, or by calibrating probabilities "
                "(e.g. CalibratedClassifierCV) instead of trusting raw predict_proba output."
            )

    if ml_wrong_when_confident:
        print("\nConfident but wrong - these are the dangerous ones, since the app shows an")
        print("answer with no signal to the user that it might be unreliable:")
        for mistake in ml_wrong_when_confident:
            print(
                f"  expected {mistake['expected']}, predicted {mistake['predicted']} "
                f"at {mistake['confidence']:.0f}% confidence"
            )

    print("\nRule of thumb: only set ML_ENABLED=true if ML confident-and-correct clearly beats")
    print("what the rule engine would have caught anyway, and confident-and-wrong stays near zero.")


if __name__ == "__main__":
    main()
