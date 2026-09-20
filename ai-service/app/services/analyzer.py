import hashlib

from app.schemas.analysis import AnalyzeLogResponse
from app.services.ml_classifier import MlClassifier
from app.services.ollama_client import OllamaClient
from app.services.rule_engine import analyze_with_rules
from app.services.static_analyzer import analyze_source_code


class LogAnalyzer:
    def __init__(self, ollama_client: OllamaClient, ml_classifier: MlClassifier) -> None:
        self._ollama_client = ollama_client
        self._ml_classifier = ml_classifier

    async def analyze(self, log_content: str, source_type: str = "GENERIC") -> AnalyzeLogResponse:
        result = analyze_with_rules(log_content, source_type)
        if result["error_category"] == "UNKNOWN":
            static_result = analyze_source_code(log_content, source_type)
            if static_result:
                result = static_result
        # An ML prediction is intentionally used only for otherwise-unknown logs.
        # Known deterministic matches remain the source of truth.
        prediction = self._ml_classifier.predict(log_content) if result["error_category"] == "UNKNOWN" else None
        if prediction:
            category, confidence = prediction
            result["error_category"] = category
            result["confidence_score"] = round(confidence, 2)
            result["summary"] = f"A trained local classifier identified this as {category.replace('_', ' ').lower()}."
            result["root_cause"] = "Review the extracted error lines to confirm this predicted category."
            key_error = result["extracted_errors"][0] if result["extracted_errors"] else category
            result["fingerprint"] = hashlib.sha256(f"{category}:{key_error.lower()}".encode()).hexdigest()
            result["analyzer_type"] = "ML"
        enrichment = await self._ollama_client.enrich(result, log_content, source_type)
        if enrichment:
            result.update(enrichment)
            result["analyzer_type"] = "OLLAMA"
            result["llm_enrichment_applied"] = True
        return AnalyzeLogResponse.model_validate(result)
