import { getStoredItems } from "./logs";

export type DashboardData = { totalUploads: number; successfulAnalyses: number; failedAnalyses: number; commonCategories: { category: string; count: number }[] };
export async function getDashboard(): Promise<DashboardData> {
  const items = getStoredItems(); const counts = new Map<string, number>();
  items.forEach(item => { const category = item.analysis.errorCategory; if (category) counts.set(category, (counts.get(category) ?? 0) + 1); });
  return { totalUploads: items.length, successfulAnalyses: items.filter(item => item.analysis.status === "COMPLETED").length, failedAnalyses: items.filter(item => item.analysis.status === "FAILED").length, commonCategories: [...counts].map(([category, count]) => ({ category, count })).sort((a, b) => b.count - a.count) };
}
