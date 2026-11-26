"use client";

import { useEffect, useState } from "react";
import { Users, RefreshCw } from "lucide-react";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Lead {
  id: string;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  company: string | null;
  job_title: string | null;
  language: string;
  created_at: string;
}

export default function LeadsTable() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchLeads = () => {
    setLoading(true);
    axios
      .get(`${API}/api/leads`)
      .then((r) => setLeads(r.data))
      .catch(() => setLeads([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchLeads();
  }, []);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Leads &amp; CRM</h1>
          <p className="text-sm text-gray-500">Customer contacts captured by SalesPilot AI</p>
        </div>
        <button onClick={fetchLeads} className="btn-secondary flex items-center gap-2 text-sm">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      <div className="card overflow-hidden p-0">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
          </div>
        ) : leads.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Users className="w-12 h-12 text-gray-700 mb-3" />
            <p className="text-gray-500">No leads yet</p>
            <p className="text-xs text-gray-600 mt-1">
              Leads are captured automatically during voice calls
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-800">
                <tr>
                  {["Name", "Email", "Company", "Job Title", "Language", "Created"].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {leads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-gray-800/50 transition-colors">
                    <td className="px-4 py-3 text-white font-medium">{lead.full_name || "—"}</td>
                    <td className="px-4 py-3 text-gray-400">{lead.email || "—"}</td>
                    <td className="px-4 py-3 text-gray-400">{lead.company || "—"}</td>
                    <td className="px-4 py-3 text-gray-400">{lead.job_title || "—"}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 bg-gray-700 rounded text-xs text-gray-300 uppercase">
                        {lead.language}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {new Date(lead.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
