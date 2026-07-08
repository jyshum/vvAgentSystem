"use client";

import { BUTTON, DecisionChip, MONO_LABEL, WhyLine, type CardProps } from "./card-shared";

export function CrawlabilityCard({ card, decision, onDecide }: CardProps) {
  return (
    <div id={`card-${card.id}`} className="p-5" style={{ border: "1px solid var(--hair)" }}>
      <div className="flex items-center gap-2 mb-3">
        <span
          className={`${MONO_LABEL} px-1.5 py-0.5`}
          style={{ color: "var(--neg)", border: "1px solid var(--neg)", background: "rgba(248,113,113,0.08)" }}
        >
          PRIORITY 0
        </span>
        <span className={MONO_LABEL} style={{ color: "var(--faint)" }}>
          FIX CRAWLABILITY
        </span>
      </div>

      <p className="font-serif text-[15px] mb-2" style={{ color: "var(--white)" }}>{card.issue}</p>
      <WhyLine card={card} />

      {decision === undefined ? (
        <div className="flex items-center gap-3 mt-3">
          <button
            onClick={() => onDecide(card.id, "approved")}
            className={BUTTON}
            style={{ border: "1px solid var(--pos)", color: "var(--pos)" }}
          >
            APPROVE
          </button>
          <button
            onClick={() => onDecide(card.id, "rejected")}
            className={BUTTON}
            style={{ border: "1px solid var(--neg)", color: "var(--neg)" }}
          >
            REJECT
          </button>
        </div>
      ) : (
        <DecisionChip decision={decision} />
      )}
    </div>
  );
}
