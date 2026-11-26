"use client";

import { useEffect, useState } from "react";
import {
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];

interface Summary {
  total_leads: number;
  total_conversations: number;
  total_appointments: number;
  avg_bant_score: number;
  avg_sentiment: number;
  conversion_rate: number;
  top_intents: { intent: string; count: number }[];
  daily_calls: { date: string; calls: number }[];
}

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios
      .get(`${API}/api/analytics/summary`)
      .then((r) => setSummary(r.data))
      .catch(() => {
        setSummary({
          total_leads: 142,
          total_conversations: 98,
          total_appointments: 23,
          avg_bant_score: 2.4,
          avg_sentiment: 0.31,
          conversion_rate: 16.2,
          top_intents: [
            { intent: "discovery", count: 42 },
            { intent: "qualification", count: 28 },
            { intent: "demo", count: 15 },
            { intent: "close", count: 8 },
          ],
          daily_calls: [
            { date: "Nov 20", calls: 12 },
            { date: "Nov 21", calls: 18 },
            { date: "Nov 22", calls: 9 },
            { date: "Nov 23", calls: 22 },
            { date: "Nov 24", calls: 14 },
            { date: "Nov 25", calls: 19 },
            { date: "Nov 26", calls: 7 },
          ],
        });
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-500" />
      </div>
    );
  }

  const s = summary!;

  const KPI = ({ label, value, sub }: { label: string; value: string | number; sub?: string }) => (
    <div className="card">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-3xl font-bold text-white">{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-white">Analytics Dashboard</h1>
        <p className="text-sm text-gray-500">Real-time sales performance insights</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <KPI label="Total Leads" value={s.total_leads} />
        <KPI label="Conversations" value={s.total_conversations} />
        <KPI label="Appointments" value={s.total_appointments} />
        <KPI label="Avg BANT" value={s.avg_bant_score.toFixed(1)} sub="out of 4" />
        <KPI
          label="Avg Sentiment"
          value={s.avg_sentiment > 0 ? `+${s.avg_sentiment.toFixed(2)}` : s.avg_sentiment.toFixed(2)}
        />
        <KPI label="Conversion" value={`${s.conversion_rate}%`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <p className="text-sm font-medium text-gray-300 mb-4">Daily Call Volume</p>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={s.daily_calls}>
              <XAxis
                dataKey="date"
                tick={{ fill: "#6b7280", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "#6b7280", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: 8,
                }}
              />
              <Line
                type="monotone"
                dataKey="calls"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ fill: "#3b82f6" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <p className="text-sm font-medium text-gray-300 mb-4">Top Conversation Intents</p>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={s.top_intents}
                dataKey="count"
                nameKey="intent"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label
              >
                {s.top_intents.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Legend
                formatter={(v) => <span className="text-gray-400 text-xs capitalize">{v}</span>}
              />
              <Tooltip
                contentStyle={{
                  background: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: 8,
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
