"""Optional local text classifier for build failures not covered by deterministic rules."""

from pathlib import Path


class MlClassifier:
    def __init__(self, enabled: bool, model_path: str, minimum_confidence: float) -> None:
        self._model = None
        self._minimum_confidence = minimum_confidence
        if not enabled:
            return
        try:
            import joblib

            path = Path(model_path)
            if path.is_file():
                self._model = joblib.load(path)
        except (ImportError, OSError, ValueError):
            # Training is optional; the rule engine remains available if no model
            # has been trained or its artifact cannot be loaded.
            self._model = None

    def predict(self, log_content: str) -> tuple[str, float] | None:
        if self._model is None:
            return None
        probabilities = self._model.predict_proba([log_content])[0]
        index = probabilities.argmax()
        confidence = float(probabilities[index]) * 100
        if confidence < self._minimum_confidence:
            return None
        return str(self._model.classes_[index]), confidence
