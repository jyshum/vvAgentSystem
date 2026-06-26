"use client";

import { useState } from "react";

interface ApprovalCardProps {
  card: {
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
  };
  clientName: string;
  onStatusChange: (cardId: string, newStatus: "approved" | "rejected") => void;
}

export function ApprovalCard({ card, clientName, onStatusChange }: ApprovalCardProps) {
  const [localStatus, setLocalStatus] = useState(card.status);

  const scoreColor = card.score >= 60 ? "var(--pos)" : card.score >= 40 ? "var(--mute)" : "var(--neg)";

  function handleApprove() {
    setLocalStatus("approved");
    onStatusChange(card.id, "approved");
  }

  function handleReject() {
    setLocalStatus("rejected");
    onStatusChange(card.id, "rejected");
  }

  return (
    <div style={{ border: "1px solid var(--hair)" }} className="p-5">
      <div className="flex items-start justify-between mb-3">
        <div className="space-y-1">
          <div className="font-mono text-[8px] tracking-[0.14em] uppercase" style={{ color: "var(--faint)" }}>
            {clientName} · {card.pillar}
          </div>
          <div className="font-mono text-[9px]" style={{ color: "var(--mute)" }}>
            {card.page_url}
          </div>
        </div>
        <span className="font-serif text-[17px]" style={{ color: scoreColor }}>
          {card.score}<span className="font-mono text-[9px] ml-0.5" style={{ color: "var(--faint)" }}>/100</span>
        </span>
      </div>

      <p className="font-serif text-[13px] mb-4" style={{ color: "var(--white)" }}>{card.issue}</p>

      {card.before_text && (
        <div className="mb-3">
          <div className="font-mono text-[8px] tracking-[0.1em] uppercase mb-1.5" style={{ color: "var(--faint)" }}>Before</div>
          <pre className="font-mono text-[10px] p-3 whitespace-pre-wrap" style={{ background: "var(--surface)", color: "var(--neg)" }}>
            {card.before_text}
          </pre>
        </div>
      )}

      {card.after_text && (
        <div className="mb-3">
          <div className="font-mono text-[8px] tracking-[0.1em] uppercase mb-1.5" style={{ color: "var(--faint)" }}>After</div>
          <pre className="font-mono text-[10px] p-3 whitespace-pre-wrap" style={{ background: "var(--surface)", color: "var(--pos)" }}>
            {card.after_text}
          </pre>
        </div>
      )}

      {card.code_block && (
        <div className="mb-3">
          <div className="font-mono text-[8px] tracking-[0.1em] uppercase mb-1.5" style={{ color: "var(--faint)" }}>Code</div>
          <pre className="font-mono text-[10px] p-3 whitespace-pre-wrap overflow-x-auto" style={{ background: "var(--surface)", color: "var(--white)" }}>
            {card.code_block}
          </pre>
        </div>
      )}

      <div className="flex items-center gap-3 mt-3">
        {localStatus === "pending" ? (
          <>
            <button
              onClick={handleApprove}
              className="font-mono text-[9px] tracking-[0.1em] uppercase px-4 py-1.5 bg-transparent cursor-pointer transition-opacity hover:opacity-70"
              style={{ border: "1px solid var(--pos)", color: "var(--pos)" }}
            >
              APPROVE
            </button>
            <button
              onClick={handleReject}
              className="font-mono text-[9px] tracking-[0.1em] uppercase px-4 py-1.5 bg-transparent cursor-pointer transition-opacity hover:opacity-70"
              style={{ border: "1px solid var(--neg)", color: "var(--neg)" }}
            >
              REJECT
            </button>
          </>
        ) : (
          <span
            className="font-mono text-[8px] tracking-[0.1em] uppercase px-2 py-0.5"
            style={{
              background: localStatus === "approved" ? "rgba(74,222,128,0.1)" : "rgba(248,113,113,0.1)",
              color: localStatus === "approved" ? "var(--pos)" : "var(--neg)",
            }}
          >
            {localStatus}
          </span>
        )}
        <span className="font-mono text-[8px]" style={{ color: "var(--faint)" }}>{card.cms_action}</span>
      </div>
    </div>
  );
}
