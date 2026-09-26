"""Persistent project memory for the LLM diagnostic engine.

The rest of this app has no server-side persistence at all - analysis history lives
only in browser localStorage (see frontend/src/api/logs.ts). That's fine for build-log
history, but "remember the previous analysis and compare" fundamentally requires state
that survives on the server, across requests and across restarts. This adds exactly
that, as plain JSON files under a data directory - no new database dependency, in
keeping with this project's existing "Docker/Postgres not required" design.

One JSON file per project_id: data/llm_project_state/{project_id}.json
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.schemas.llm_diagnostics import (
    ComparisonResult, Finding, IssueRecord, ProjectHistoryEntry, ProjectStateSnapshot,
)

_SAFE_PROJECT_ID = re.compile(r"^[A-Za-z0-9_-]{1,200}$")


class ProjectContextManager:
    def __init__(self, data_dir: str | Path = "data/llm_project_state") -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, project_id: str) -> Path:
        # project_id becomes a filename - reject anything that isn't a safe slug to
        # avoid path traversal (e.g. project_id="../../etc/passwd").
        if not _SAFE_PROJECT_ID.match(project_id):
            raise ValueError("project_id must be 1-200 characters of letters, digits, '_' or '-'.")
        return self._data_dir / f"{project_id}.json"

    def load(self, project_id: str) -> dict:
        path = self._path_for(project_id)
        if not path.is_file():
            return {"project_id": project_id, "issues": {}, "history": []}
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, project_id: str, state: dict) -> None:
        path = self._path_for(project_id)
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def record_analysis(self, project_id: str, findings: list[Finding]) -> tuple[str, "ComparisonResult"]:
        """Saves a new analysis, updates issue statuses, and returns (analysis_id, comparison)."""
        state = self.load(project_id)
        analysis_id = f"analysis_{uuid4().hex[:10]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        previous_open_problems = {
            record["problem"] for record in state["issues"].values()
            if record["status"] not in ("VERIFIED",)
        }
        current_problems = {finding.problem for finding in findings if finding.category != "UNKNOWN"}

        still_working: list[str] = []
        fixed: list[str] = []
        for record in list(state["issues"].values()):
            if record["status"] == "VERIFIED":
                if record["problem"] in current_problems:
                    # A previously-verified fix shows the same problem again - regression,
                    # not "still working".
                    record["status"] = "REGRESSED"
                    record["last_seen_analysis_id"] = analysis_id
                else:
                    still_working.append(record["problem"])
        for problem in previous_open_problems - current_problems:
            # Was open before, isn't showing up now - candidate fix, but section 10 says
            # never auto-claim VERIFIED. Mark IN_PROGRESS; a human/test confirms VERIFIED
            # via the mark-verified endpoint.
            for record in state["issues"].values():
                if record["problem"] == problem and record["status"] not in ("VERIFIED",):
                    record["status"] = "IN_PROGRESS"
                    fixed.append(problem)

        newly_broken: list[str] = []
        unresolved: list[str] = []
        for finding in findings:
            if finding.category == "UNKNOWN":
                continue
            existing = next((r for r in state["issues"].values() if r["problem"] == finding.problem), None)
            if existing is None:
                finding_id = f"finding_{uuid4().hex[:10]}"
                state["issues"][finding_id] = {
                    "finding_id": finding_id, "category": finding.category, "problem": finding.problem,
                    "status": "PROPOSED", "first_seen_analysis_id": analysis_id, "last_seen_analysis_id": analysis_id,
                }
                newly_broken.append(finding.problem)
            else:
                existing["last_seen_analysis_id"] = analysis_id
                if existing["status"] not in ("VERIFIED", "IN_PROGRESS"):
                    unresolved.append(finding.problem)
                elif existing["status"] == "IN_PROGRESS":
                    # Proposed-as-fixed but the same problem is back - the fix didn't hold.
                    existing["status"] = "FAILED"
                    unresolved.append(finding.problem)

        if newly_broken:
            recommended_next_step = f"Investigate the new issue(s) first: {'; '.join(newly_broken[:2])}."
        elif unresolved:
            recommended_next_step = f"Continue working on the unresolved issue(s): {'; '.join(unresolved[:2])}."
        elif fixed:
            recommended_next_step = f"Verify the apparent fix(es) with a real test before trusting them: {'; '.join(fixed[:2])}."
        else:
            recommended_next_step = "No open issues detected. Re-analyze after the next change to this LLM integration."

        comparison = ComparisonResult(
            still_working=still_working, fixed=fixed, unresolved=unresolved,
            newly_broken=newly_broken, recommended_next_step=recommended_next_step,
        )
        state["history"].append({
            "analysis_id": analysis_id, "timestamp": timestamp,
            "findings_summary": [f"{f.category}: {f.problem}" for f in findings],
            "comparison": comparison.model_dump(),
        })
        self.save(project_id, state)
        return analysis_id, comparison

    def get_snapshot(self, project_id: str) -> ProjectStateSnapshot:
        state = self.load(project_id)
        issues = [IssueRecord(**record) for record in state["issues"].values()]
        return ProjectStateSnapshot(
            project_id=project_id, analysis_count=len(state["history"]), issues_detected=issues,
            last_analysis_id=state["history"][-1]["analysis_id"] if state["history"] else None,
            last_updated=state["history"][-1]["timestamp"] if state["history"] else None,
        )

    def get_history(self, project_id: str) -> list[ProjectHistoryEntry]:
        state = self.load(project_id)
        return [
            ProjectHistoryEntry(
                analysis_id=entry["analysis_id"], timestamp=entry["timestamp"],
                findings_summary=entry["findings_summary"],
                comparison=ComparisonResult(**entry["comparison"]) if entry.get("comparison") else None,
            )
            for entry in state["history"]
        ]

    def get_unresolved_issues(self, project_id: str) -> list[IssueRecord]:
        state = self.load(project_id)
        return [IssueRecord(**record) for record in state["issues"].values() if record["status"] not in ("VERIFIED",)]

    def mark_status(self, project_id: str, finding_id: str, status: str) -> IssueRecord | None:
        state = self.load(project_id)
        record = state["issues"].get(finding_id)
        if record is None:
            return None
        record["status"] = status
        self.save(project_id, state)
        return IssueRecord(**record)
