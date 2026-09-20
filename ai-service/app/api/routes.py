from fastapi import APIRouter, Request

from app.schemas.analysis import AnalyzeLogRequest, AnalyzeLogResponse, HealthResponse

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(status="UP", ollama_enabled=settings.ollama_enabled)


@router.post("/analyze", response_model=AnalyzeLogResponse)
async def analyze_log(payload: AnalyzeLogRequest, request: Request) -> AnalyzeLogResponse:
    return await request.app.state.analyzer.analyze(payload.log_content, payload.source_type)
