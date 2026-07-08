"use client";

import { useState } from "react";
import { BUTTON, DecisionChip, MONO_LABEL, WhyLine, type CardProps } from "./card-shared";

export function CommunityCheckCard({ card, decision, onDecide }: CardProps) {
  const [threadUrl, setThreadUrl] = useState("");
  const links = card.reddit_data?.search_links;
  const guidance = card.reddit_data?.guidance;

  return (
    <div id={`card-${card.id}`} className="p-5" style={{ border: "1px solid var(--hair)" }}>
      <div className={`${MONO_LABEL} mb-3`} style={{ color: "var(--faint)" }}>
        COMMUNITY CHECK
      </div>
      <p className="font-serif text-[13px] mb-2" style={{ color: "var(--white)" }}>{card.issue}</p>
      <WhyLine card={card} />

      <div className="flex items-center gap-3 mb-3">
        {links?.reddit && (
          <a
            href={links.reddit}
            target="_blank"
            rel="noreferrer"
            className={BUTTON}
            style={{ border: "1px solid var(--faint)", color: "var(--faint)", textDecoration: "none" }}
          >
            SEARCH REDDIT &rarr;
          </a>
        )}
        {links?.google && (
          <a
            href={links.google}
            target="_blank"
            rel="noreferrer"
            className={BUTTON}
            style={{ border: "1px solid var(--faint)", color: "var(--faint)", textDecoration: "none" }}
          >
            GOOGLE SITE:REDDIT &rarr;
          </a>
        )}
      </div>

      {guidance && (
        <p className="font-serif italic text-[12px] mb-3" style={{ color: "var(--mute)" }}>
          {guidance}
        </p>
      )}

      {decision === undefined ? (
        <div className="flex items-center gap-3 mt-3">
          <input
            type="text"
            value={threadUrl}
            onChange={(e) => setThreadUrl(e.target.value)}
            placeholder="engaged thread URL (optional)"
            className="font-mono text-[10px] px-2 py-1.5"
            style={{ background: "transparent", border: "1px solid var(--hair)", color: "var(--white)" }}
          />
          <button
            onClick={() => onDecide(card.id, "approved")}
            className={BUTTON}
            style={{ border: "1px solid var(--pos)", color: "var(--pos)" }}
          >
            MARK DONE
          </button>
          <button
            onClick={() => onDecide(card.id, "rejected")}
            className={BUTTON}
            style={{ border: "1px solid var(--neg)", color: "var(--neg)" }}
          >
            SKIP
          </button>
        </div>
      ) : (
        <DecisionChip decision={decision} />
      )}
    </div>
  );
}
