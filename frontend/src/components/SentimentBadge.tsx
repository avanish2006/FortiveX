"use client";

import { clsx } from "clsx";

export default function SentimentBadge({ label, score }: { label: string; score: number }) {
  const icon = label === "positive" ? "😊" : label === "negative" ? "😟" : "😐";
  const color =
    label === "positive"
      ? "text-green-400"
      : label === "negative"
      ? "text-red-400"
      : "text-yellow-400";

  return (
    <div className="flex items-center gap-2">
      <span className="text-xl">{icon}</span>
      <div>
        <p className={clsx("text-sm font-semibold capitalize", color)}>{label}</p>
        <p className="text-xs text-gray-600">
          {score >= 0 ? "+" : ""}
          {score.toFixed(2)}
        </p>
      </div>
    </div>
  );
}
