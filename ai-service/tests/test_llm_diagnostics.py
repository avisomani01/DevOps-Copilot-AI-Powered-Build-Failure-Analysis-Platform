from fastapi.testclient import TestClient

from app.main import create_app


def _client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("LLM_PROJECT_STATE_DIR", str(tmp_path))
    return TestClient(create_app())


def test_timeout_detection_with_no_timeout_in_code(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    response = client.post("/api/v1/analyze-llm", json={
        "project_id": "proj1",
        "llm_code": "response = ollama.generate(model='llama3.2:3b', prompt=prompt)",
        "error_info": "Requests time out under load.",
    })
    assert response.status_code == 200
    findings = response.json()["findings"]
    assert any(f["category"] == "TIMEOUT" and f["evidence_level"] == "LIKELY" for f in findings)


def test_blocking_call_in_async_is_confirmed(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    code = "async def call_model(prompt):\n    response = requests.post('http://x', json={'p': prompt})\n    return response.json()"
    response = client.post("/api/v1/analyze-llm", json={"project_id": "proj2", "llm_code": code})
    findings = response.json()["findings"]
    assert any(f["category"] == "CODE_INTEGRATION" and f["evidence_level"] == "CONFIRMED" for f in findings)


def test_invalid_json_detection(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    response = client.post("/api/v1/analyze-llm", json={
        "project_id": "proj3",
        "llm_code": "data = json.loads(response.text)",
        "error_info": "Response parsing fails: invalid JSON returned by the model.",
    })
    findings = response.json()["findings"]
    assert any(f["category"] == "PARSING_FAILURE" for f in findings)


def test_context_loss_detection(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    response = client.post("/api/v1/analyze-llm", json={
        "project_id": "proj4",
        "llm_code": "response = ollama.generate(model='x', prompt=prompt)",
        "error_info": "The assistant forgets previous analysis every time.",
    })
    findings = response.json()["findings"]
    assert any(f["category"] == "CONTEXT_PROBLEM" and f["evidence_level"] == "LIKELY" for f in findings)


def test_hallucination_detection_with_high_temperature(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    response = client.post("/api/v1/analyze-llm", json={
        "project_id": "proj5",
        "prompt": "Explain the error in this log.",
        "error_info": "The model hallucinated a stack trace that never happened.",
        "config": {"temperature": 1.2},
    })
    findings = response.json()["findings"]
    assert any(f["category"] == "HALLUCINATION" and f["evidence_level"] == "LIKELY" for f in findings)


def test_prompt_format_mismatch_detection(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    response = client.post("/api/v1/analyze-llm", json={
        "project_id": "proj6",
        "prompt": "Analyze this log and explain the error.",
        "expected_response": "The model should identify the root cause and return 3 concrete fixes.",
        "actual_response": "I am unable to determine the issue.",
    })
    findings = response.json()["findings"]
    assert any(f["category"] == "PROMPT_PROBLEM" and f["evidence_level"] == "LIKELY" for f in findings)


def test_insufficient_evidence_when_nothing_matches(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    response = client.post("/api/v1/analyze-llm", json={"project_id": "proj7"})
    findings = response.json()["findings"]
    assert len(findings) == 1
    assert findings[0]["evidence_level"] == "INSUFFICIENT_EVIDENCE"
    assert findings[0]["category"] == "UNKNOWN"


def test_project_state_persists_across_requests(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    client.post("/api/v1/analyze-llm", json={"project_id": "proj8", "error_info": "Requests time out under load."})
    state = client.get("/api/v1/project/proj8/state").json()
    assert state["analysis_count"] == 1
    assert len(state["issues_detected"]) == 1
    assert state["issues_detected"][0]["category"] == "TIMEOUT"


def test_history_accumulates_across_multiple_analyses(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    client.post("/api/v1/analyze-llm", json={"project_id": "proj9", "error_info": "Requests time out under load."})
    client.post("/api/v1/analyze-llm", json={"project_id": "proj9", "error_info": "Requests time out under load."})
    history = client.get("/api/v1/project/proj9/history").json()
    assert len(history["entries"]) == 2


def test_issue_that_stops_appearing_is_marked_fixed_candidate_not_auto_verified(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    client.post("/api/v1/analyze-llm", json={"project_id": "proj10", "error_info": "Requests time out under load."})
    second = client.post("/api/v1/analyze-llm", json={"project_id": "proj10"}).json()
    assert "The LLM call is timing out or hanging." in second["compared_to_previous"]["fixed"]
    state = client.get("/api/v1/project/proj10/state").json()
    # Section 10: never auto-claim VERIFIED - it should be IN_PROGRESS, a human/test must confirm.
    assert state["issues_detected"][0]["status"] == "IN_PROGRESS"


def test_verified_issue_that_reappears_is_marked_regressed(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    first = client.post("/api/v1/analyze-llm", json={"project_id": "proj11", "error_info": "Requests time out under load."}).json()
    finding_id = client.get("/api/v1/project/proj11/state").json()["issues_detected"][0]["finding_id"]
    client.post("/api/v1/project/proj11/feedback", json={"finding_id": finding_id, "status": "VERIFIED"})
    second = client.post("/api/v1/analyze-llm", json={"project_id": "proj11", "error_info": "Requests time out under load."}).json()
    state = client.get("/api/v1/project/proj11/state").json()
    assert state["issues_detected"][0]["status"] == "REGRESSED"


def test_candidate_fix_that_regresses_is_marked_failed(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    client.post("/api/v1/analyze-llm", json={"project_id": "proj12", "error_info": "Requests time out under load."})
    client.post("/api/v1/analyze-llm", json={"project_id": "proj12"})  # looks fixed -> IN_PROGRESS
    client.post("/api/v1/analyze-llm", json={"project_id": "proj12", "error_info": "Requests time out under load."})  # back again
    state = client.get("/api/v1/project/proj12/state").json()
    assert state["issues_detected"][0]["status"] == "FAILED"


def test_continue_debugging_returns_unresolved_issue(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    client.post("/api/v1/analyze-llm", json={"project_id": "proj13", "error_info": "Requests time out under load."})
    response = client.post("/api/v1/continue-debugging", json={"project_id": "proj13"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["unresolved_issues"]) == 1
    assert "timing out" in body["recommended_next_step"]


def test_continue_debugging_with_no_history_says_so(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    response = client.post("/api/v1/continue-debugging", json={"project_id": "brand-new-project"})
    assert response.status_code == 200
    assert "No unresolved issues" in response.json()["recommended_next_step"]


def test_invalid_project_id_is_rejected(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    response = client.get("/api/v1/project/../../etc/state")
    # Path traversal attempt should not be treated as a valid project id.
    assert response.status_code in (400, 404)


def test_existing_endpoints_unaffected_by_llm_diagnostics_addition(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    analyze = client.post("/api/v1/analyze", json={"log_content": "ModuleNotFoundError: No module named 'fastapi'"})
    assert analyze.status_code == 200
    assert analyze.json()["error_category"] == "PYTHON_MODULE"
