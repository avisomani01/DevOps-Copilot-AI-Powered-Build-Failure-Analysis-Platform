import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.services.analyzer import LogAnalyzer
from app.services.llm_diagnostic_engine import LlmDiagnosticEngine
from app.services.ml_classifier import MlClassifier
from app.services.ollama_client import OllamaClient
from app.services.project_context_manager import ProjectContextManager
from app.services.settings import Settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def create_app() -> FastAPI:
    app = FastAPI(title="DevOps Copilot Lite AI Service", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):\d+",
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    settings = Settings.from_environment()
    app.state.settings = settings
    app.state.analyzer = LogAnalyzer(OllamaClient(settings), MlClassifier(settings.ml_enabled, settings.ml_model_path, settings.ml_minimum_confidence))
    context_manager = ProjectContextManager(data_dir=settings.llm_project_state_dir)
    app.state.context_manager = context_manager
    app.state.diagnostic_engine = LlmDiagnosticEngine(context_manager)
    app.include_router(router)
    return app


app = create_app()
