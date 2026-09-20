from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeLogRequest(BaseModel):
    log_content: str = Field(min_length=1, max_length=2_000_000)
    source_type: str = Field(default="GENERIC", max_length=30)


class AnalyzeLogResponse(BaseModel):
    error_category: str
    confidence_score: float = Field(ge=0, le=100)
    summary: str
    root_cause: str
    extracted_errors: list[str]
    suggested_fixes: list[str]
    fingerprint: str
    analyzer_type: Literal["OLLAMA", "RULE_BASED", "ML", "STATIC"]
    llm_enrichment_applied: bool = False


class HealthResponse(BaseModel):
    status: str
    ollama_enabled: bool
