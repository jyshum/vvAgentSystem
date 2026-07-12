"use client";

import { useEffect, useState } from "react";

interface CompetitorCount {
  name: string;
  count: number;
}

interface MentionEvidence {
  wording: string;
  sentence: string;
  brand: string;
}

interface EngineDetail {
  engine: string;
  total: number;
  mentionedCount: number;
  citedCount: number;
  mentioned: boolean;
  cited: boolean;
  citationUrl: string | null;
  mentions: MentionEvidence[];
  competitorsNamed: CompetitorCount[];
  wordings: string[];
}

interface QueryExpansionProps {
  clientId: string;
  query: string;
  queryId?: string | null;
}

type LoadState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; engines: EngineDetail[] };

function HighlightedSentence({ sentence, brand }: { sentence: string; brand: string }) {
  const lower = sentence.toLowerCase();
  const idx = lower.indexOf(brand.toLowerCase());
  if (idx === -1) {
    return <span>{sentence}</span>;
  }
  const before = sentence.slice(0, idx);
  const match = sentence.slice(idx, idx + brand.length);
  const after = sentence.slice(idx + brand.length);
  return (
    <span>
      {before}
      <mark style={{ background: "rgba(132,216,171,0.25)", color: "var(--white)" }}>{match}</mark>
      {after}
    </span>
  );
}

export function QueryExpansion({ clientId, query, queryId }: QueryExpansionProps) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams();
    if (queryId) params.set("query_id", queryId);
    params.set("query", query);
    fetch(`/api/admin/query-detail/${clientId}?${params.toString()}`)
      .then((res) => {
        if (!res.ok) throw new Error("failed");
        return res.json();
      })
      .then((data) => {
        if (!cancelled) setState({ status: "ready", engines: data.engines ?? [] });
      })
      .catch(() => {
        if (!cancelled) setState({ status: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [clientId, query, queryId]);

  if (state.status === "loading") {
    return (
      <div className="px-4 py-4 font-mono text-[9px]" style={{ color: "var(--faint)" }}>
        LOADING…
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="px-4 py-4 font-mono text-[9px]" style={{ color: "var(--neg)" }}>
        FAILED TO LOAD
      </div>
    );
  }

  return (
    <div className="px-4 py-2">
      {state.engines.map((eng) => (
        <div
          key={eng.engine}
          className="py-3 px-3 mb-2 border"
          style={{ borderColor: "var(--hair)", background: "var(--ink-soft)" }}
        >
          <div className="font-mono text-[9px] tracking-[0.1em] uppercase mb-1" style={{ color: "var(--white)" }}>
            {eng.engine}
          </div>
          <div className="font-mono text-[9px] mb-1.5" style={{ color: "var(--mute)" }}>
            mentioned {eng.mentionedCount}/{eng.total} wordings · cited {eng.citedCount}/{eng.total} wordings
          </div>
          {eng.wordings.length > 1 && (
            <div className="font-mono text-[8px] mb-1.5" style={{ color: "var(--faint)" }}>
              {eng.wordings.length} wordings sampled
            </div>
          )}
          {eng.mentions.map((m, i) => (
            <div key={i} className="mb-1.5">
              <div className="font-serif text-[13px]" style={{ color: "var(--white)" }}>
                <HighlightedSentence sentence={m.sentence} brand={m.brand} />
              </div>
              <div className="font-mono text-[8px] mt-0.5" style={{ color: "var(--faint)" }}>
                wording: &ldquo;{m.wording}&rdquo;
              </div>
            </div>
          ))}
          {eng.cited && eng.citationUrl && (
            <a
              href={eng.citationUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-[9px] underline block mb-1"
              style={{ color: "var(--mute)" }}
            >
              {eng.citationUrl}
            </a>
          )}
          {eng.competitorsNamed.length > 0 ? (
            <div
              className="font-serif text-[12px]"
              style={{ color: eng.mentioned ? "#d4a017" : "var(--neg)" }}
            >
              {eng.mentioned ? "co-mentioned with competitors: " : "answer recommended: "}
              {eng.competitorsNamed.map((c) => `${c.name} ${c.count}/${eng.total}`).join(", ")}
            </div>
          ) : (
            <div className="font-serif text-[12px]" style={{ color: "var(--faint)" }}>
              no competitors named
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
