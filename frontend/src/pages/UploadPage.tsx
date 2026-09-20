import { useState } from "react";
import type { ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { analyzeLog, uploadLog } from "../api/logs";

export function UploadPage() {
  const [file, setFile] = useState<File | null>(null); const [error, setError] = useState(""); const [isUploading, setIsUploading] = useState(false); const navigate = useNavigate();
  const selectFile = (event: ChangeEvent<HTMLInputElement>) => { setError(""); const selected = event.target.files?.[0] ?? null; if (selected && selected.size > 2 * 1024 * 1024) { setError("Choose a UTF-8 text-based file no larger than 2 MB."); setFile(null); return; } setFile(selected); };
  const submit = async () => { if (!file) return; setError(""); setIsUploading(true); try { const log = await uploadLog(file); await analyzeLog(log.id); navigate(`/analysis/${log.id}`); } catch (exception) { const message = axios.isAxiosError(exception) ? exception.response?.data?.message : exception instanceof Error ? exception.message : "Unknown error"; setError(message ? `Analysis failed: ${message}` : "Analysis failed. Confirm the Python AI service is running at http://127.0.0.1:8000."); } finally { setIsUploading(false); } };
  return <><header className="mb-7"><p className="text-sm font-medium text-blue-600">NEW ANALYSIS</p><h1 className="text-3xl font-bold">Upload a file to analyze</h1><p className="mt-2 text-slate-600">Upload a UTF-8 log, source, or configuration file up to 2 MB. Secrets should be removed before upload.</p></header>
    <section className="card max-w-2xl p-6"><label className="block cursor-pointer rounded-xl border-2 border-dashed border-slate-300 p-10 text-center transition hover:border-blue-400 hover:bg-blue-50"><input className="sr-only" type="file" accept="text/*,.log,.txt,.java,.py,.js,.ts,.tsx,.jsx,.go,.rs,.c,.h,.cpp,.hpp,.cs,.php,.rb,.swift,.kt,.kts,.scala,.sh,.ps1,.sql,.xml,.json,.yaml,.yml,.toml,.ini,.properties,.gradle,.dockerfile" onChange={selectFile} /><span className="text-lg font-semibold">Choose a log, source, or config file</span><span className="mt-2 block text-sm text-slate-500">Supports common programming languages, build files, configuration files, and logs</span></label>
    {file && <div className="mt-5 rounded-lg bg-slate-50 p-4 text-sm"><span className="font-semibold">Selected:</span> {file.name} <span className="text-slate-500">({Math.ceil(file.size / 1024)} KB)</span></div>}
    {error && <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
    <button disabled={!file || isUploading} onClick={submit} className="btn-primary mt-6">{isUploading ? "Analyzing..." : "Upload and analyze"}</button></section></>;
}
