"use client";

import { BUTTON, DecisionChip, MONO_LABEL, WhyLine, type CardProps } from "./card-shared";

export function BriefCard({ card, decision, onDecide }: CardProps) {
  const brief = card.brief;

  return (
    <div id={`card-${card.id}`} className="p-5" style={{ border: "1px solid var(--hair)" }}>
      <div className={`${MONO_LABEL} mb-3`} style={{ color: "var(--faint)" }}>
        CONTENT BRIEF
      </div>
      <WhyLine card={card} />

      {brief ? (
        <div className="space-y-3">
          <div className="font-display text-[20px] font-light" style={{ color: "var(--white)" }}>
            {brief.recommended_title}
          </div>
          <div className="font-mono text-[9px]" style={{ color: "var(--mute)" }}>
            H1: {brief.recommended_h1}
          </div>
          <div>
            <div className={`${MONO_LABEL} mb-1.5`} style={{ color: "var(--faint)" }}>Key Sections</div>
            <ul className="font-serif text-[13px] list-disc pl-5 space-y-1" style={{ color: "var(--white)" }}>
              {brief.key_sections.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
          <div>
            <div className={`${MONO_LABEL} mb-1.5`} style={{ color: "var(--faint)" }}>Facts to Include</div>
            <ul className="font-serif text-[13px] list-disc pl-5 space-y-1" style={{ color: "var(--white)" }}>
              {brief.facts_to_include.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          </div>
          <div className={MONO_LABEL} style={{ color: "var(--faint)" }}>
            SCHEMA {brief.schema_type} · TARGET {brief.word_count_target} WORDS
          </div>
        </div>
      ) : (
        <p className="font-serif text-[13px]" style={{ color: "var(--white)" }}>{card.issue}</p>
      )}

      <div className="flex items-center gap-3 mt-4">
        {decision === undefined ? (
          <>
            <button
              onClick={() => onDecide(card.id, "approved")}
              className={BUTTON}
              style={{ border: "1px solid var(--pos)", color: "var(--pos)" }}
            >
              ACCEPT &amp; ASSIGN
            </button>
            <button
              onClick={() => onDecide(card.id, "rejected")}
              className={BUTTON}
              style={{ border: "1px solid var(--neg)", color: "var(--neg)" }}
            >
              REJECT
            </button>
          </>
        ) : (
          <DecisionChip decision={decision} />
        )}
      </div>
    </div>
  );
}
