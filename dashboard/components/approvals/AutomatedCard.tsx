"use client";

import { BUTTON, DecisionChip, MONO_LABEL, WhyLine, type CardProps } from "./card-shared";

export function AutomatedCard({ card, decision, onDecide }: CardProps) {
  const score = card.structural_score;
  const scoreColor =
    score == null ? "var(--mute)" : score >= 60 ? "var(--pos)" : score >= 40 ? "var(--mute)" : "var(--neg)";

  return (
    <div id={`card-${card.id}`} className="p-5" style={{ border: "1px solid var(--hair)" }}>
      <div className="flex items-start justify-between mb-3">
        <div className="space-y-1">
          <div className={MONO_LABEL} style={{ color: "var(--faint)" }}>
            {card.action_type}
          </div>
          {card.page_url && (
            <div className="font-mono text-[9px]" style={{ color: "var(--mute)" }}>
              {card.page_url}
            </div>
          )}
        </div>
        {score != null && (
          <span className="font-serif text-[17px]" style={{ color: scoreColor }}>
            {score}
            <span className="font-mono text-[9px] ml-0.5" style={{ color: "var(--faint)" }}>/100</span>
          </span>
        )}
      </div>

      <p className="font-serif text-[13px] mb-2" style={{ color: "var(--white)" }}>{card.issue}</p>
      <WhyLine card={card} />

      {card.before_text && (
        <div className="mb-3">
          <div className={`${MONO_LABEL} mb-1.5`} style={{ color: "var(--faint)" }}>Before</div>
          <pre className="font-mono text-[10px] p-3 whitespace-pre-wrap" style={{ background: "var(--ink-2)", color: "var(--neg)" }}>
            {card.before_text}
          </pre>
        </div>
      )}

      {card.after_text && (
        <div className="mb-3">
          <div className={`${MONO_LABEL} mb-1.5`} style={{ color: "var(--faint)" }}>After</div>
          <pre className="font-mono text-[10px] p-3 whitespace-pre-wrap" style={{ background: "var(--ink-2)", color: "var(--pos)" }}>
            {card.after_text}
          </pre>
        </div>
      )}

      {card.code_block && (
        <div className="mb-3">
          <div className={`${MONO_LABEL} mb-1.5`} style={{ color: "var(--faint)" }}>Code</div>
          <pre className="font-mono text-[10px] p-3 whitespace-pre-wrap overflow-x-auto" style={{ background: "var(--ink-2)", color: "var(--white)" }}>
            {card.code_block}
          </pre>
        </div>
      )}

      <div className="flex items-center gap-3 mt-3">
        {decision === undefined ? (
          <>
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
            {card.page_url && (
              <a
                href={card.page_url}
                target="_blank"
                rel="noreferrer"
                className={BUTTON}
                style={{ border: "1px solid var(--faint)", color: "var(--faint)", textDecoration: "none" }}
              >
                VIEW PAGE
              </a>
            )}
          </>
        ) : (
          <DecisionChip decision={decision} />
        )}
      </div>
    </div>
  );
}
