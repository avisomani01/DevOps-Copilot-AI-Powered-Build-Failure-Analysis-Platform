import axios from "axios";

const aiBaseUrl = import.meta.env.VITE_AI_SERVICE_URL ?? "http://127.0.0.1:8000/api/v1";

export type ModelConfig = { model_name?: string; temperature?: number; max_tokens?: number; context_window?: number; system_prompt?: string; timeout_seconds?: number; top_p?: number; api_endpoint?: string; retry_count?: number };

export type Finding = { category: string; evidence_level: "CONFIRMED" | "LIKELY" | "POSSIBLE" | "INSUFFICIENT_EVIDENCE"; problem: string; evidence: string[]; root_cause: string; recommended_fix: string; code_change: string | null; expected_result: string; verification_method: string; next_step_if_it_fails: string };

export type ComparisonResult = { still_working: string[]; fixed: string[]; unresolved: string[]; newly_broken: string[]; recommended_next_step: string };

export type AnalyzeLlmResponse = { project_id: string; analysis_id: string; timestamp: string; findings: Finding[]; overall_note: string; compared_to_previous: ComparisonResult | null };

export type IssueRecord = { finding_id: string; category: string; problem: string; status: string; first_seen_analysis_id: string; last_seen_analysis_id: string };

export type ProjectHistoryEntry = { analysis_id: string; timestamp: string; findings_summary: string[]; comparison: ComparisonResult | null };

export async function analyzeLlm(input: { project_id: string; llm_code?: string; prompt?: string; expected_response?: string; actual_response?: string; error_info?: string; config?: ModelConfig }): Promise<AnalyzeLlmResponse> {
  return (await axios.post<AnalyzeLlmResponse>(`${aiBaseUrl}/analyze-llm`, input)).data;
}

export async function getProjectHistory(projectId: string): Promise<ProjectHistoryEntry[]> {
  return (await axios.get<{ project_id: string; entries: ProjectHistoryEntry[] }>(`${aiBaseUrl}/project/${encodeURIComponent(projectId)}/history`)).data.entries;
}

export async function getProjectState(projectId: string): Promise<{ project_id: string; analysis_count: number; issues_detected: IssueRecord[] }> {
  return (await axios.get(`${aiBaseUrl}/project/${encodeURIComponent(projectId)}/state`)).data;
}

export async function continueDebugging(projectId: string): Promise<{ unresolved_issues: IssueRecord[]; recommended_next_step: string; reasoning: string }> {
  return (await axios.post(`${aiBaseUrl}/continue-debugging`, { project_id: projectId })).data;
}

export async function markFindingStatus(projectId: string, findingId: string, status: string): Promise<void> {
  await axios.post(`${aiBaseUrl}/project/${encodeURIComponent(projectId)}/feedback`, { finding_id: findingId, status });
}
