"use client";

import { useState } from "react";
import { ApprovalCard } from "./ApprovalCard";

interface Card {
  id: string;
  page_url: string;
  pillar: string;
  score: number;
  issue: string;
  before_text: string;
  after_text: string;
  code_block: string;
  status: string;
  cms_action: string;
  client_name?: string;
}

interface PipelineRun {
  thread_id: string;
  client_id: string;
}

export function ApprovalsClient({ initialCards, pipelineRuns }: { initialCards: Card[]; pipelineRuns: PipelineRun[] }) {
  const [decisions, setDecisions] = useState<Record<string, "approved" | "rejected">>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  function handleStatusChange(cardId: string, newStatus: "approved" | "rejected") {
    setDecisions(prev => ({ ...prev, [cardId]: newStatus }));
  }

  const approvedIds = Object.entries(decisions).filter(([, s]) => s === "approved").map(([id]) => id);
  const hasDecisions = Object.keys(decisions).length > 0;

  async function finalize() {
    setSubmitting(true);
    try {
      const threadId = pipelineRuns[0]?.thread_id || null;
      const res = await fetch("/api/admin/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ threadId, approvedCardIds: approvedIds }),
      });
      if (!res.ok) {
        const body = await res.json();
        throw new Error(body.error || "Failed to finalize");
      }
      setSubmitted(true);
    } catch (err) {
      console.error("Finalize failed:", err);
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div className="text-center py-20">
        <div className="font-serif italic text-base" style={{ color: "var(--pos)" }}>
          {approvedIds.length} card{approvedIds.length !== 1 ? "s" : ""} approved and sent to implementation.
        </div>
      </div>
    );
  }

  if (initialCards.length === 0) {
    return (
      <div className="text-center py-20">
        <div className="font-serif italic text-base" style={{ color: "var(--mute)" }}>
          No pending action cards.
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="space-y-4 mb-10">
        {initialCards.map(card => (
          <ApprovalCard
            key={card.id}
            card={card}
            clientName={card.client_name || "Unknown"}
            onStatusChange={handleStatusChange}
          />
        ))}
      </div>

      {hasDecisions && (
        <div className="flex items-center gap-4">
          <button
            onClick={finalize}
            disabled={submitting || approvedIds.length === 0}
            className="font-mono text-[10px] tracking-[0.14em] uppercase py-3 px-7 transition-all duration-200 hover:opacity-80 disabled:cursor-not-allowed disabled:opacity-40"
            style={{ background: "var(--pos)", color: "var(--ink)", border: "none" }}
          >
            {submitting ? "IMPLEMENTING..." : `FINALIZE & IMPLEMENT (${approvedIds.length})`}
          </button>
          <span className="font-mono text-[8px]" style={{ color: "var(--faint)" }}>
            {Object.values(decisions).filter(s => s === "rejected").length} rejected
          </span>
        </div>
      )}
    </div>
  );
}
