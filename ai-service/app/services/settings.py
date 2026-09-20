import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ollama_enabled: bool
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_seconds: float
    ollama_max_code_characters: int
    ml_enabled: bool
    ml_model_path: str
    ml_minimum_confidence: float

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            ollama_enabled=os.getenv("OLLAMA_ENABLED", "false").lower() == "true",
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            ollama_timeout_seconds=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "45")),
            ollama_max_code_characters=int(os.getenv("OLLAMA_MAX_CODE_CHARACTERS", "60000")),
            ml_enabled=os.getenv("ML_ENABLED", "false").lower() == "true",
            ml_model_path=os.getenv("ML_MODEL_PATH", "models/log_classifier.joblib"),
            ml_minimum_confidence=float(os.getenv("ML_MINIMUM_CONFIDENCE", "60")),
        )
