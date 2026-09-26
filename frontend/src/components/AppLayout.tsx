import { NavLink, Outlet } from "react-router-dom";

const links = [["/dashboard", "Dashboard"], ["/upload", "Upload log"], ["/history", "Build history"], ["/llm-debug", "LLM Debugging"]];

export function AppLayout() {
  return <div className="min-h-screen md:flex">
    <aside className="border-b border-slate-200 bg-white px-4 py-4 md:min-h-screen md:w-64 md:border-b-0 md:border-r">
      <div className="mb-5 flex items-center gap-2 font-bold text-ink"><span className="grid h-8 w-8 place-items-center rounded-lg bg-blue-600 text-white">D</span> DevOps Copilot</div>
      <nav className="flex gap-1 overflow-x-auto md:flex-col">{links.map(([to, label]) => <NavLink key={to} to={to} className={({ isActive }) => `whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium ${isActive ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-100"}`}>{label}</NavLink>)}</nav>
      <div className="mt-5 border-t pt-4 text-sm text-slate-500 md:mt-auto">Build-failure analysis workspace</div>
    </aside>
    <main className="mx-auto w-full max-w-6xl p-5 md:p-8"><Outlet /></main>
  </div>;
}
