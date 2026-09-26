import { useState } from "react";
import axios from "axios";
import { analyzeLlm, continueDebugging, getProjectHistory, getProjectState, markFindingStatus } from "../api/llmDebug";
import type { AnalyzeLlmResponse, Finding, ProjectHistoryEntry } from "../api/llmDebug";

const evidenceColor: Record<string, string> = {
  CONFIRMED: "bg-rose-50 text-rose-700 border-rose-300",
  LIKELY: "bg-amber-50 text-amber-700 border-amber-300",
  POSSIBLE: "bg-blue-50 text-blue-700 border-blue-300",
  INSUFFICIENT_EVIDENCE: "bg-slate-50 text-slate-600 border-slate-300",
};

function FindingCard({ finding }: { finding: Finding }) {
  return <article className="card space-y-3 border p-5">
    <div className="flex flex-wrap items-center gap-2">
      <span className="rounded bg-slate-100 px-2 py-1 text-xs font-bold">{finding.category}</span>
      <span className={`rounded border px-2 py-1 text-xs font-bold ${evidenceColor[finding.evidence_level]}`}>{finding.evidence_level}</span>
    </div>
    <p className="font-semibold">{finding.problem}</p>
    <div><p className="text-xs font-bold uppercase text-slate-500">Evidence</p><ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">{finding.evidence.map(e => <li key={e}>{e}</li>)}</ul></div>
    <div><p className="text-xs font-bold uppercase text-slate-500">Root cause</p><p className="text-sm text-slate-700">{finding.root_cause}</p></div>
    <div><p className="text-xs font-bold uppercase text-slate-500">Recommended fix</p><p className="text-sm text-slate-700">{finding.recommended_fix}</p></div>
    {finding.code_change && <div><p className="text-xs font-bold uppercase text-slate-500">Example code change</p><pre className="mt-1 overflow-x-auto rounded bg-slate-900 p-3 text-xs text-slate-100">{finding.code_change}</pre></div>}
    <div><p className="text-xs font-bold uppercase text-slate-500">Expected result</p><p className="text-sm text-slate-700">{finding.expected_result}</p></div>
    <div><p className="text-xs font-bold uppercase text-slate-500">Verification method</p><p className="text-sm text-slate-700">{finding.verification_method}</p></div>
    <div><p className="text-xs font-bold uppercase text-slate-500">If it doesn't work</p><p className="text-sm text-slate-700">{finding.next_step_if_it_fails}</p></div>
  </article>;
}

export function LlmDebugPage() {
  const [projectId, setProjectId] = useState("my-devops-copilot");
  const [llmCode, setLlmCode] = useState("");
  const [prompt, setPrompt] = useState("");
  const [expected, setExpected] = useState("");
  const [actual, setActual] = useState("");
  const [errorInfo, setErrorInfo] = useState("");
  const [result, setResult] = useState<AnalyzeLlmResponse | null>(null);
  const [history, setHistory] = useState<ProjectHistoryEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function refreshHistory() {
    try { setHistory(await getProjectHistory(projectId)); } catch { setHistory([]); }
  }

  async function handleAnalyze() {
    setBusy(true); setError("");
    try {
      const response = await analyzeLlm({ project_id: projectId, llm_code: llmCode || undefined, prompt: prompt || undefined, expected_response: expected || undefined, actual_response: actual || undefined, error_info: errorInfo || undefined });
      setResult(response);
      await refreshHistory();
    } catch (exception) {
      setError(axios.isAxiosError(exception) ? exception.response?.data?.detail ?? "Analysis failed." : "Analysis failed. Confirm the Python AI service is running at http://127.0.0.1:8000.");
    } finally { setBusy(false); }
  }

  async function handleContinueDebugging() {
    setBusy(true); setError("");
    try {
      const response = await continueDebugging(projectId);
      setResult({ project_id: projectId, analysis_id: "continue-debugging", timestamp: new Date().toISOString(), findings: [], overall_note: response.reasoning, compared_to_previous: null });
      await refreshHistory();
      window.alert(`Recommended next step:\n\n${response.recommended_next_step}`);
    } catch {
      setError("Could not fetch debugging history. Has this project ever been analyzed?");
    } finally { setBusy(false); }
  }

  async function handleMarkVerified(findingId: string) {
    await markFindingStatus(projectId, findingId, "VERIFIED");
    await refreshHistory();
    window.alert("Marked as VERIFIED. This will only be reported as regressed if the same problem is detected again in a future analysis.");
  }

  return <div className="space-y-6">
    <div><h1 className="text-3xl font-bold">LLM Debugging Assistant</h1><p className="mt-2 text-slate-600">Diagnose why an LLM feature isn't behaving as expected, and track fixes across re-analyses.</p></div>

    <section className="card space-y-4 p-6">
      <div><label className="text-sm font-semibold">Project ID (used to remember history across analyses)</label><input className="mt-1 w-full rounded-lg border border-slate-300 p-2 text-sm" value={projectId} onChange={e => setProjectId(e.target.value)} /></div>
      <div><label className="text-sm font-semibold">LLM implementation code</label><textarea className="mt-1 h-32 w-full rounded-lg border border-slate-300 p-2 font-mono text-sm" placeholder="e.g. response = ollama.generate(model='llama3.2:3b', prompt=prompt)" value={llmCode} onChange={e => setLlmCode(e.target.value)} /></div>
      <div><label className="text-sm font-semibold">Prompt</label><textarea className="mt-1 h-20 w-full rounded-lg border border-slate-300 p-2 text-sm" value={prompt} onChange={e => setPrompt(e.target.value)} /></div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div><label className="text-sm font-semibold">Expected response</label><textarea className="mt-1 h-24 w-full rounded-lg border border-slate-300 p-2 text-sm" value={expected} onChange={e => setExpected(e.target.value)} /></div>
        <div><label className="text-sm font-semibold">Actual response</label><textarea className="mt-1 h-24 w-full rounded-lg border border-slate-300 p-2 text-sm" value={actual} onChange={e => setActual(e.target.value)} /></div>
      </div>
      <div><label className="text-sm font-semibold">Error / log info</label><textarea className="mt-1 h-20 w-full rounded-lg border border-slate-300 p-2 text-sm" placeholder="e.g. Timeout, Invalid JSON, Empty response, Hallucinated response..." value={errorInfo} onChange={e => setErrorInfo(e.target.value)} /></div>
      <div className="flex flex-wrap gap-3">
        <button className="btn-primary" disabled={busy} onClick={handleAnalyze}>{busy ? "Analyzing..." : "Analyze LLM"}</button>
        <button className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50" disabled={busy} onClick={handleContinueDebugging}>Continue Debugging</button>
      </div>
      {error && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
    </section>

    {result && result.compared_to_previous && <section className="card space-y-2 border-2 border-blue-200 bg-blue-50 p-6">
      <h2 className="font-bold text-blue-900">Compared to previous analysis</h2>
      <p className="text-sm text-blue-900"><strong>Recommended next step:</strong> {result.compared_to_previous.recommended_next_step}</p>
      {result.compared_to_previous.newly_broken.length > 0 && <p className="text-sm"><strong>New:</strong> {result.compared_to_previous.newly_broken.join("; ")}</p>}
      {result.compared_to_previous.unresolved.length > 0 && <p className="text-sm"><strong>Still unresolved:</strong> {result.compared_to_previous.unresolved.join("; ")}</p>}
      {result.compared_to_previous.fixed.length > 0 && <p className="text-sm"><strong>Appears fixed (not yet verified):</strong> {result.compared_to_previous.fixed.join("; ")}</p>}
      {result.compared_to_previous.still_working.length > 0 && <p className="text-sm"><strong>Confirmed still working:</strong> {result.compared_to_previous.still_working.join("; ")}</p>}
    </section>}

    {result && result.findings.length > 0 && <section className="space-y-4"><h2 className="text-xl font-bold">Findings</h2><p className="text-sm text-slate-600">{result.overall_note}</p>{result.findings.map(f => <FindingCard key={f.problem} finding={f} />)}</section>}

    <section className="card p-6">
      <div className="flex items-center justify-between"><h2 className="font-bold">Debugging timeline for "{projectId}"</h2><button className="text-sm font-semibold text-blue-600" onClick={refreshHistory}>Refresh</button></div>
      {history.length === 0 ? <p className="mt-3 text-sm text-slate-500">No analyses recorded yet for this project ID.</p> : <ol className="mt-4 space-y-4 border-l-2 border-slate-200 pl-5">
        {history.map((entry, index) => <li key={entry.analysis_id} className="relative">
          <span className="absolute -left-[27px] top-1 h-3 w-3 rounded-full bg-blue-500" />
          <p className="text-xs font-semibold text-slate-500">Analysis #{index + 1} — {new Date(entry.timestamp).toLocaleString()}</p>
          <ul className="mt-1 list-disc pl-5 text-sm text-slate-700">{entry.findings_summary.map(s => <li key={s}>{s}</li>)}</ul>
          {entry.comparison && <p className="mt-1 text-xs italic text-slate-500">Next step at the time: {entry.comparison.recommended_next_step}</p>}
        </li>)}
      </ol>}
    </section>

    <section className="card p-6">
      <h2 className="font-bold">Mark a finding verified</h2>
      <p className="mt-1 text-sm text-slate-600">After you've actually re-tested a fix, mark it verified so future analyses can detect a real regression instead of just "not currently appearing".</p>
      <FindingVerifier projectId={projectId} onVerify={handleMarkVerified} />
    </section>
  </div>;
}

function FindingVerifier({ projectId, onVerify }: { projectId: string; onVerify: (findingId: string) => void }) {
  const [findingId, setFindingId] = useState("");
  return <div className="mt-3 flex gap-2">
    <input className="flex-1 rounded-lg border border-slate-300 p-2 text-sm" placeholder="finding_id (see project state)" value={findingId} onChange={e => setFindingId(e.target.value)} />
    <button className="btn-primary" disabled={!findingId} onClick={() => { onVerify(findingId); setFindingId(""); }}>Mark Verified</button>
    <ViewStateLink projectId={projectId} />
  </div>;
}

function ViewStateLink({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(false);
  const [ids, setIds] = useState<string[]>([]);
  return <div className="relative">
    <button className="rounded-lg border border-slate-300 px-3 py-2 text-sm" onClick={async () => { setOpen(!open); if (!open) { const state = await getProjectState(projectId); setIds(state.issues_detected.map(i => `${i.finding_id} — ${i.category}: ${i.problem} [${i.status}]`)); } }}>Show IDs</button>
    {open && <div className="absolute right-0 z-10 mt-2 w-96 rounded-lg border border-slate-300 bg-white p-3 text-xs shadow-lg">{ids.length === 0 ? <p>No issues on record.</p> : <ul className="space-y-1">{ids.map(id => <li key={id}>{id}</li>)}</ul>}</div>}
  </div>;
}
