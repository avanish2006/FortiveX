"use client";

import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import VoiceAgent from "@/components/VoiceAgent";
import Dashboard from "@/components/Dashboard";
import KnowledgeBase from "@/components/KnowledgeBase";
import LeadsTable from "@/components/LeadsTable";

type View = "agent" | "dashboard" | "knowledge" | "leads";

export default function Home() {
  const [view, setView] = useState<View>("agent");

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      <Sidebar activeView={view} setView={setView} />
      <main className="flex-1 overflow-y-auto">
        {view === "agent" && <VoiceAgent />}
        {view === "dashboard" && <Dashboard />}
        {view === "knowledge" && <KnowledgeBase />}
        {view === "leads" && <LeadsTable />}
      </main>
    </div>
  );
}
