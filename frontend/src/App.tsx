import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { AnalysisPage } from "./pages/AnalysisPage";
import { DashboardPage } from "./pages/DashboardPage";
import { HistoryPage } from "./pages/HistoryPage";
import { LlmDebugPage } from "./pages/LlmDebugPage";
import { UploadPage } from "./pages/UploadPage";

export default function App() {
  return <Routes>
    <Route element={<AppLayout />}>
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/upload" element={<UploadPage />} />
      <Route path="/history" element={<HistoryPage />} />
      <Route path="/analysis/:id" element={<AnalysisPage />} />
      <Route path="/llm-debug" element={<LlmDebugPage />} />
    </Route>
    <Route path="*" element={<Navigate to="/dashboard" replace />} />
  </Routes>;
}
