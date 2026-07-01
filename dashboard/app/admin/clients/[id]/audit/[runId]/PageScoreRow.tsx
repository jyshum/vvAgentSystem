"use client";

import { useState } from "react";

interface PillarData {
  score: number;
  strengths?: string[];
  issues?: string[];
  recommendations?: string[];
}

interface PageScore {
  id: string;
  url: string;
  title: string;
  word_count: number;
  total_score: number;
  pillar_scores: Record<string, PillarData>;
}

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 60 ? "var(--green, #4ade80)" : score >= 40 ? "var(--yellow, #facc15)" : "var(--red, #f87171)";
  return (
    <span className="font-serif text-[17px]" style={{ color }}>
      {score}
      <span className="font-mono text-[9px] ml-0.5" style={{ color: "var(--faint)" }}>/100</span>
    </span>
  );
}

function SmallScore({ score }: { score: number }) {
  const color =
    score >= 60 ? "var(--green, #4ade80)" : score >= 40 ? "var(--yellow, #facc15)" : "var(--red, #f87171)";
  return (
    <span className="font-mono text-[12px]" style={{ color }}>
      {score}
    </span>
  );
}

export function PageScoreRow({ page }: { page: PageScore }) {
  const [open, setOpen] = useState(false);
  const pillars = page.pillar_scores || {};
  const pillarEntries = Object.entries(pillars);

  return (
    <div style={{ borderBottom: "1px solid var(--hair)" }}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full grid py-3 text-left cursor-pointer bg-transparent border-none transition-colors hover:bg-[rgba(255,255,255,0.02)]"
        style={{ gridTemplateColumns: "1fr 80px", gap: "16px" }}
      >
        <span className="font-mono text-[10px] truncate" style={{ color: "var(--mute)" }}>
          <span style={{ color: "var(--faint)", marginRight: 6 }}>{open ? "▾" : "▸"}</span>
          {page.url.replace(/^https?:\/\//, "")}
          <a
            href={page.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="ml-2 font-mono text-[8px] tracking-[0.1em] uppercase transition-colors hover:text-[var(--white)]"
            style={{ color: "var(--faint)", textDecoration: "none" }}
          >
            ↗ open
          </a>
        </span>
        <ScoreBadge score={page.total_score} />
      </button>

      {open && (
        <div className="pb-4 pl-6 pr-4 space-y-3">
          {(page.title || page.word_count > 0) && (
            <div className="font-mono text-[9px]" style={{ color: "var(--faint)" }}>
              {page.title && <span>{page.title}</span>}
              {page.title && page.word_count > 0 && <span> · </span>}
              {page.word_count > 0 && <span>{page.word_count} words</span>}
            </div>
          )}

          {pillarEntries.length > 0 ? (
            <div className="grid grid-cols-3 gap-2">
              {pillarEntries.map(([name, pillar]) => (
                <div key={name} className="p-2.5" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--hair)" }}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[8px] tracking-[0.1em] uppercase" style={{ color: "var(--faint)" }}>
                      {name}
                    </span>
                    <SmallScore score={pillar.score} />
                  </div>

                  {pillar.strengths && pillar.strengths.length > 0 && (
                    <div className="mb-1.5">
                      {pillar.strengths.map((s, i) => (
                        <div key={i} className="font-mono text-[9px] leading-relaxed" style={{ color: "var(--green, #4ade80)" }}>
                          + {s}
                        </div>
                      ))}
                    </div>
                  )}

                  {pillar.issues && pillar.issues.length > 0 && (
                    <div className="mb-1.5">
                      {pillar.issues.map((s, i) => (
                        <div key={i} className="font-mono text-[9px] leading-relaxed" style={{ color: "var(--red, #f87171)" }}>
                          − {s}
                        </div>
                      ))}
                    </div>
                  )}

                  {pillar.recommendations && pillar.recommendations.length > 0 && (
                    <div>
                      {pillar.recommendations.map((s, i) => (
                        <div key={i} className="font-mono text-[9px] leading-relaxed" style={{ color: "var(--mute)" }}>
                          → {s}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="font-mono text-[9px]" style={{ color: "var(--faint)" }}>
              No pillar data available
            </div>
          )}
        </div>
      )}
    </div>
  );
}
