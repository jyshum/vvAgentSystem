"use client";

import type { ActionCard } from "@/lib/improvement-types";
import { formatRate } from "@/lib/utils";

/** Exact set of action_cards columns selected by the approvals page and read by
 * the card components. Kept as a Pick subset (not full ActionCard) so a card
 * component can never read an un-selected column as `undefined` without TS error. */
export type ReviewCardData = Pick<
  ActionCard,
  | "id"
  | "run_id"
  | "client_id"
  | "query_id"
  | "page_url"
  | "action_type"
  | "track"
  | "priority"
  | "competitive_gap"
  | "structural_score"
  | "issue"
  | "before_text"
  | "after_text"
  | "code_block"
  | "status"
  | "cms_action"
  | "auto_approved"
  | "brief"
  | "reddit_data"
  | "created_at"
>;

export type ReviewCard = ReviewCardData & { queryText: string | null };
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
