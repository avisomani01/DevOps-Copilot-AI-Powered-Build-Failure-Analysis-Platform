from fastapi.testclient import TestClient

from app.main import create_app


def test_analyze_endpoint_uses_rule_based_fallback(monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_ENABLED", "false")
    client = TestClient(create_app())
    response = client.post("/api/v1/analyze", json={"log_content": "ModuleNotFoundError: No module named 'fastapi'"})
    assert response.status_code == 200
    assert response.json()["error_category"] == "PYTHON_MODULE"
    assert response.json()["analyzer_type"] == "RULE_BASED"


def test_analyze_endpoint_rejects_empty_log() -> None:
    client = TestClient(create_app())
    response = client.post("/api/v1/analyze", json={"log_content": ""})
    assert response.status_code == 422


def test_large_code_context_keeps_line_numbers_and_stays_bounded() -> None:
    from app.services.ollama_client import OllamaClient

    source = "\n".join(f"def function_{number}(): return {number}" for number in range(5_000))
    context = OllamaClient._build_code_context(source, 1_000)
    assert len(context) <= 1_100
    assert "def function_0" in context
