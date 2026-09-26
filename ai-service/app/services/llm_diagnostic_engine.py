"""Orchestrates llm_response_analyzer.py (evidence-based diagnosis) and
project_context_manager.py (persistent memory) into the full diagnose -> compare ->
recommend workflow described in the project spec's sections 4-10.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.llm_diagnostics import AnalyzeLlmRequest, AnalyzeLlmResponse
from app.services import llm_response_analyzer
from app.services.project_context_manager import ProjectContextManager


class LlmDiagnosticEngine:
    def __init__(self, context_manager: ProjectContextManager) -> None:
        self._context_manager = context_manager

    def analyze(self, request: AnalyzeLlmRequest) -> AnalyzeLlmResponse:
        findings = llm_response_analyzer.analyze(request)
        analysis_id, comparison = self._context_manager.record_analysis(request.project_id, findings)

        if any(f.evidence_level == "INSUFFICIENT_EVIDENCE" for f in findings) and len(findings) == 1:
            overall_note = "No specific failure pattern could be confirmed from the supplied information - see the single finding below for what more would help."
        else:
            confirmed = sum(1 for f in findings if f.evidence_level in ("CONFIRMED", "LIKELY"))
            overall_note = f"{confirmed} of {len(findings)} finding(s) have solid supporting evidence (CONFIRMED/LIKELY); review evidence_level on each before acting."

        return AnalyzeLlmResponse(
            project_id=request.project_id,
            analysis_id=analysis_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings=findings,
            overall_note=overall_note,
            compared_to_previous=comparison,
        )
