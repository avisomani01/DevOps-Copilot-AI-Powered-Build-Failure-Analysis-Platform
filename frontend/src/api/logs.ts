import axios from "axios";

export type UploadedLog = { id: string; originalFilename: string; sourceType: string; uploadStatus: string; uploadedAt: string };
export type LogPage = { content: UploadedLog[]; page: number; size: number; totalElements: number; totalPages: number };
export type AnalysisResult = { id: string; buildLogId: string; status: string; errorCategory: string | null; confidenceScore: number | null; summary: string | null; rootCause: string | null; extractedErrors: string[]; suggestedFixes: string[]; analyzerType: string | null; failureReason: string | null; incidentOccurrenceCount: number; analyzedAt: string | null };
export type IncidentResult = { analysisId: string; buildLogId: string; filename: string; category: string; summary: string; rootCause: string; occurrenceCount: number; analyzedAt: string };

type AiResponse = { error_category: string; confidence_score: number; summary: string; root_cause: string; extracted_errors: string[]; suggested_fixes: string[]; analyzer_type: string };
type StoredItem = { log: UploadedLog; analysis: AnalysisResult };

const storageKey = "devopsCopilotLocalAnalyses";
const aiBaseUrl = import.meta.env.VITE_AI_SERVICE_URL ?? "http://127.0.0.1:8000/api/v1";

function readItems(): StoredItem[] {
  try { return JSON.parse(localStorage.getItem(storageKey) ?? "[]") as StoredItem[]; }
  catch { return []; }
}
function writeItems(items: StoredItem[]) { localStorage.setItem(storageKey, JSON.stringify(items)); }
function detectSourceType(filename: string, content: string): string {
  const name = filename.toLowerCase(); const text = content.toLowerCase();
  if (name.endsWith(".py") || text.includes("traceback") || text.includes("modulenotfounderror")) return "PYTHON";
  if (name.endsWith(".gradle") || text.includes("gradle")) return "GRADLE";
  if (name.endsWith(".java") || text.includes("maven") || text.includes("pom.xml")) return text.includes("maven") ? "MAVEN" : "JAVA";
  if (name.endsWith(".js") || name.endsWith(".jsx")) return "JAVASCRIPT";
  if (name.endsWith(".ts") || name.endsWith(".tsx")) return "TYPESCRIPT";
  if (name.endsWith(".go")) return "GO";
  if (name.endsWith(".rs")) return "RUST";
  if (name.endsWith(".c") || name.endsWith(".h")) return "C";
  if (name.endsWith(".cpp") || name.endsWith(".hpp")) return "CPP";
  if (name.endsWith(".cs")) return "CSHARP";
  if (name.endsWith(".php")) return "PHP";
  if (name.endsWith(".rb")) return "RUBY";
  if (name.endsWith(".swift")) return "SWIFT";
  if (name.endsWith(".kt") || name.endsWith(".kts")) return "KOTLIN";
  if (name.includes("dockerfile") || text.includes("docker build")) return "DOCKER";
  if (text.includes("jenkins") || text.includes("hudson.")) return "JENKINS";
  return "GENERIC";
}

export function getStoredItems(): StoredItem[] { return readItems(); }
export async function uploadLog(file: File): Promise<UploadedLog> {
  const content = await file.text();
  if (!content.trim()) throw new Error("The selected file is empty or is not readable UTF-8 text.");
  const sourceType = detectSourceType(file.name, content);
  const ai = (await axios.post<AiResponse>(`${aiBaseUrl}/analyze`, { log_content: content, source_type: sourceType })).data;
  const now = new Date().toISOString(); const logId = crypto.randomUUID(); const analysisId = crypto.randomUUID();
  const log: UploadedLog = { id: logId, originalFilename: file.name, sourceType, uploadStatus: "ANALYZED", uploadedAt: now };
  const analysis: AnalysisResult = { id: analysisId, buildLogId: logId, status: "COMPLETED", errorCategory: ai.error_category, confidenceScore: ai.confidence_score, summary: ai.summary, rootCause: ai.root_cause, extractedErrors: ai.extracted_errors, suggestedFixes: ai.suggested_fixes, analyzerType: ai.analyzer_type, failureReason: null, incidentOccurrenceCount: 1, analyzedAt: now };
  writeItems([{ log, analysis }, ...readItems()]);
  return log;
}
export async function getLogs(): Promise<LogPage> { const content = readItems().map(item => item.log); return { content, page: 0, size: 20, totalElements: content.length, totalPages: 1 }; }
export async function analyzeLog(logId: string): Promise<AnalysisResult> { return getAnalysis(logId); }
export async function getAnalysis(logId: string): Promise<AnalysisResult> { const item = readItems().find(entry => entry.log.id === logId); if (!item) throw new Error("Analysis not found"); return item.analysis; }
export async function searchIncidents(category: string): Promise<IncidentResult[]> { return readItems().filter(item => item.analysis.errorCategory === category).map(item => ({ analysisId: item.analysis.id, buildLogId: item.log.id, filename: item.log.originalFilename, category, summary: item.analysis.summary ?? "", rootCause: item.analysis.rootCause ?? "", occurrenceCount: 1, analyzedAt: item.analysis.analyzedAt ?? item.log.uploadedAt })); }
