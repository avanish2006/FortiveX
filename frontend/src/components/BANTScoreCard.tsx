"use client";

import { clsx } from "clsx";

const BANT_LABELS = ["Budget", "Authority", "Need", "Timeline"];
const COLORS = ["bg-red-500", "bg-orange-500", "bg-yellow-500", "bg-green-500", "bg-green-400"];
const QUAL_LABELS = ["Cold", "Warm", "Interested", "Hot", "Ready"];

export default function BANTScoreCard({ score }: { score: number }) {
  const pct = (score / 4) * 100;
  const color = COLORS[score] ?? COLORS[0];
  const label = QUAL_LABELS[score] ?? "Cold";

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs text-gray-500">BANT Score</p>
        <span className={clsx("text-xs px-2 py-0.5 rounded-full text-white font-medium", color)}>
          {label}
        </span>
      </div>
      <div className="flex items-end gap-1 mb-2">
        <span className="text-3xl font-bold text-white">{score}</span>
        <span className="text-gray-500 text-sm mb-1">/4</span>
      </div>
      <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={clsx("h-full rounded-full transition-all duration-500", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between mt-2">
        {BANT_LABELS.map((l) => (
          <span key={l} className="text-[10px] text-gray-600">
            {l[0]}
          </span>
        ))}
      </div>
    </div>
  );
}
