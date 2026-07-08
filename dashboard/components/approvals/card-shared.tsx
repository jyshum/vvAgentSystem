"use client";

import type { ActionCard } from "@/lib/improvement-types";
import { formatRate } from "@/lib/utils";

export type ReviewCard = ActionCard & { queryText: string | null };
export type Decision = "approved" | "rejected";

export interface CardProps {
  card: ReviewCard;
  decision: Decision | undefined;
  onDecide: (cardId: string, decision: Decision) => void;
}

export const MONO_LABEL =
  "font-mono text-[8px] tracking-[0.1em] uppercase";

export const BUTTON =
  "font-mono text-[9px] tracking-[0.1em] uppercase px-4 py-1.5 bg-transparent cursor-pointer transition-opacity hover:opacity-70";

export function WhyLine({ card }: { card: ReviewCard }) {
  return (
    <div className="font-mono text-[9px] mb-3" style={{ color: "var(--faint)" }}>
      target: &quot;{card.queryText ?? card.page_url ?? "site"}&quot;
      {card.competitive_gap != null && card.competitive_gap > 0 && (
        <> · gap {formatRate(card.competitive_gap)}</>
      )}
    </div>
  );
}

export function DecisionChip({ decision }: { decision: Decision }) {
  return (
    <span
      className={`${MONO_LABEL} px-2 py-0.5`}
      style={{
        background: decision === "approved" ? "rgba(74,222,128,0.1)" : "rgba(248,113,113,0.1)",
        color: decision === "approved" ? "var(--pos)" : "var(--neg)",
      }}
    >
      {decision}
    </span>
  );
}
