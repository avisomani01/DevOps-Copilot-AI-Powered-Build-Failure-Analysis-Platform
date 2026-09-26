"""Schemas for the LLM diagnostic engine and persistent project memory.

Follows the same pattern as analysis.py (one flat file per feature area) rather than
introducing a separate app/models/ package, to match how this project already
organizes its schemas.
"""

from typing import Literal

from pydantic import BaseModel, Field

# Evidence-based confidence labels. Never a bare percentage pulled from nowhere -
# see llm_response_analyzer.py for how each label is actually earned.
EvidenceLevel = Literal["CONFIRMED", "LIKELY", "POSSIBLE", "INSUFFICIENT_EVIDENCE"]

DiagnosticCategory = Literal[
    "PROMPT_PROBLEM", "CONTEXT_PROBLEM", "MODEL_CONFIGURATION", "MODEL_CAPABILITY",
    "TOKEN_LIMIT", "CONTEXT_WINDOW", "API_FAILURE", "TIMEOUT", "PARSING_FAILURE",
    "OUTPUT_FORMAT_FAILURE", "HALLUCINATION", "TOOL_FAILURE", "MEMORY_FAILURE",
    "RETRIEVAL_FAILURE", "CODE_INTEGRATION", "STATE_MANAGEMENT", "UNKNOWN",
]

FixStatus = Literal["PROPOSED", "IN_PROGRESS", "VERIFIED", "FAILED", "REGRESSED", "UNKNOWN"]


class ModelConfig(BaseModel):
    """All optional - section 3 says don't require fields that aren't available."""
    model_name: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    context_window: int | None = None
    system_prompt: str | None = None
    timeout_seconds: float | None = None
    top_p: float | None = None
    api_endpoint: str | None = None
    retry_count: int | None = None


class AnalyzeLlmRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=200)
    llm_code: str | None = Field(default=None, max_length=200_000)
    prompt: str | None = Field(default=None, max_length=200_000)
    expected_response: str | None = Field(default=None, max_length=20_000)
    actual_response: str | None = Field(default=None, max_length=20_000)
    error_info: str | None = Field(default=None, max_length=20_000)
    config: ModelConfig | None = None


class Finding(BaseModel):
    category: DiagnosticCategory
    evidence_level: EvidenceLevel
    problem: str
    evidence: list[str]
    root_cause: str
    recommended_fix: str
    code_change: str | None = None
    expected_result: str
    verification_method: str
    next_step_if_it_fails: str


class AnalyzeLlmResponse(BaseModel):
    project_id: str
    analysis_id: str
    timestamp: str
    findings: list[Finding]
    overall_note: str
    compared_to_previous: "ComparisonResult | None" = None


class IssueRecord(BaseModel):
    finding_id: str
    category: DiagnosticCategory
    problem: str
    status: FixStatus = "PROPOSED"
    first_seen_analysis_id: str
    last_seen_analysis_id: str


class ComparisonResult(BaseModel):
    still_working: list[str] = Field(default_factory=list)
    fixed: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    newly_broken: list[str] = Field(default_factory=list)
    recommended_next_step: str


class ProjectStateSnapshot(BaseModel):
    project_id: str
    analysis_count: int
    issues_detected: list[IssueRecord] = Field(default_factory=list)
    last_analysis_id: str | None = None
    last_updated: str | None = None


class ProjectHistoryEntry(BaseModel):
    analysis_id: str
    timestamp: str
    findings_summary: list[str]
    comparison: ComparisonResult | None = None


class ProjectHistoryResponse(BaseModel):
    project_id: str
    entries: list[ProjectHistoryEntry]


class MarkVerifiedRequest(BaseModel):
    finding_id: str
    status: FixStatus
    verification_note: str | None = Field(default=None, max_length=2000)


class ContinueDebuggingRequest(BaseModel):
    project_id: str
    current_llm_code: str | None = Field(default=None, max_length=200_000)
    current_error_info: str | None = Field(default=None, max_length=20_000)


class ContinueDebuggingResponse(BaseModel):
    project_id: str
    unresolved_issues: list[IssueRecord]
    recommended_next_step: str
    reasoning: str
