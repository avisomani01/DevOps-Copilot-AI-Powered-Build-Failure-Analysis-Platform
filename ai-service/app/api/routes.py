from fastapi import APIRouter, HTTPException, Request

from app.schemas.analysis import AnalyzeLogRequest, AnalyzeLogResponse, HealthResponse
from app.schemas.llm_diagnostics import (
    AnalyzeLlmRequest, AnalyzeLlmResponse, ContinueDebuggingRequest, ContinueDebuggingResponse,
    MarkVerifiedRequest, ProjectHistoryResponse, ProjectStateSnapshot,
)

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(status="UP", ollama_enabled=settings.ollama_enabled)


@router.post("/analyze", response_model=AnalyzeLogResponse)
async def analyze_log(payload: AnalyzeLogRequest, request: Request) -> AnalyzeLogResponse:
    return await request.app.state.analyzer.analyze(payload.log_content, payload.source_type)


@router.post("/analyze-llm", response_model=AnalyzeLlmResponse, tags=["llm-diagnostics"])
async def analyze_llm(payload: AnalyzeLlmRequest, request: Request) -> AnalyzeLlmResponse:
    return request.app.state.diagnostic_engine.analyze(payload)


@router.get("/project/{project_id}/history", response_model=ProjectHistoryResponse, tags=["llm-diagnostics"])
async def project_history(project_id: str, request: Request) -> ProjectHistoryResponse:
    try:
        entries = request.app.state.context_manager.get_history(project_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ProjectHistoryResponse(project_id=project_id, entries=entries)


@router.get("/project/{project_id}/state", response_model=ProjectStateSnapshot, tags=["llm-diagnostics"])
async def project_state(project_id: str, request: Request) -> ProjectStateSnapshot:
    try:
        return request.app.state.context_manager.get_snapshot(project_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/project/{project_id}/feedback", tags=["llm-diagnostics"])
async def project_feedback(project_id: str, payload: MarkVerifiedRequest, request: Request) -> dict:
    record = request.app.state.context_manager.mark_status(project_id, payload.finding_id, payload.status)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No finding '{payload.finding_id}' found for project '{project_id}'.")
    return {"finding_id": record.finding_id, "status": record.status}


@router.post("/continue-debugging", response_model=ContinueDebuggingResponse, tags=["llm-diagnostics"])
async def continue_debugging(payload: ContinueDebuggingRequest, request: Request) -> ContinueDebuggingResponse:
    context_manager = request.app.state.context_manager
    try:
        unresolved = context_manager.get_unresolved_issues(payload.project_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not unresolved:
        return ContinueDebuggingResponse(
            project_id=payload.project_id, unresolved_issues=[],
            recommended_next_step="No unresolved issues on record. Submit a new /analyze-llm request if a new problem has appeared.",
            reasoning="Project state currently has no open (non-VERIFIED) issues.",
        )
    priority = unresolved[0]
    return ContinueDebuggingResponse(
        project_id=payload.project_id, unresolved_issues=unresolved,
        recommended_next_step=f"Focus on: {priority.problem} (category: {priority.category}, status: {priority.status}).",
        reasoning=f"This is the longest-standing unresolved issue on record for this project (first seen in {priority.first_seen_analysis_id}, still open as of {priority.last_seen_analysis_id}).",
    )
