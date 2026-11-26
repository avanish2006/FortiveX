"use client";

import { Mic, BarChart3, BookOpen, Users, Zap } from "lucide-react";
import { clsx } from "clsx";

type View = "agent" | "dashboard" | "knowledge" | "leads";

const NAV_ITEMS: { id: View; label: string; icon: React.ReactNode }[] = [
  { id: "agent", label: "Voice Agent", icon: <Mic className="w-5 h-5" /> },
  { id: "dashboard", label: "Analytics", icon: <BarChart3 className="w-5 h-5" /> },
  { id: "knowledge", label: "Knowledge Base", icon: <BookOpen className="w-5 h-5" /> },
  { id: "leads", label: "Leads & CRM", icon: <Users className="w-5 h-5" /> },
];

export default function Sidebar({
  activeView,
  setView,
}: {
  activeView: View;
  setView: (v: View) => void;
}) {
  return (
    <aside className="w-60 bg-gray-900 border-r border-gray-800 flex flex-col shrink-0">
      <div className="px-5 py-5 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="text-sm font-bold text-white">SalesPilot AI</p>
            <p className="text-[10px] text-gray-500 uppercase tracking-wider">Voice Agent</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            onClick={() => setView(item.id)}
            className={clsx(
              "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
              activeView === item.id
                ? "bg-brand-600 text-white"
                : "text-gray-400 hover:bg-gray-800 hover:text-gray-100"
            )}
          >
            {item.icon}
            {item.label}
          </button>
        ))}
      </nav>

      <div className="px-4 py-4 border-t border-gray-800">
        <p className="text-xs text-gray-600">SalesPilot AI v1.0</p>
        <p className="text-xs text-gray-700">Autonomous Sales Agent</p>
      </div>
    </aside>
  );
}
