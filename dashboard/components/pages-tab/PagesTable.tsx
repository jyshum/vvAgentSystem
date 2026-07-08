"use client";

import { useState } from "react";
import Link from "next/link";
import { formatRate } from "@/lib/utils";
import type { CheckResult, SonnetQuality, PageCitationScore } from "@/lib/improvement-types";

export interface PageRowData {
  url: string;
  title: string;
  score: number | null; // page_citation_scores.structural_score; null = not scored (unmatched page)
  schemaStatus: PageCitationScore["schema_status"] | null; // null when not scored
  hasFaq: boolean; // page_inventory.has_faq_schema
  hasComparison: boolean; // page_inventory.has_comparison_table
  wordCount: number;
  lastModified: string | null;
  queriesServed: { query: string; similarity: number; weak: boolean }[]; // query_page_matches by matched_page_url
  checks: Record<string, CheckResult> | null; // check_results jsonb
  schemaErrors: string[];
  sonnet: SonnetQuality | null;
  waitingCards: { id: string; action_type: string }[]; // pending cards with page_url === url
}

export interface ContentGapRow {
  query: string;
  topCompetitor: string | null; // competitive_gaps competitor_data max mention_rate name
  gap: number | null; // that competitor's rate − client rate (competitive_gaps client_mention_rate), or null when no competitor_data
  briefCardId: string | null; // pending action_cards with action_type='content_brief' matching the gap query's query_id
}

interface PagesTableProps {
  rows: PageRowData[];
  gaps: ContentGapRow[];
}

const CHECK_ORDER = [
  "answer_first",
  "faq_schema",
  "comparison_tables",
  "lists",
  "freshness",
  "word_count",
  "source_citations",
  "author_attribution",
  "schema_validation",
];

function checkLabel(key: string): string {
  return key.replace(/_/g, " ").toUpperCase();
}

function pagePathname(url: string): string {
  try {
    return new URL(url).pathname;
  } catch {
    return url;
  }
}

function readinessColor(score: number): string {
  if (score >= 70) return "var(--pos)";
  if (score >= 40) return "#ffc107";
  return "var(--neg)";
}

const SCHEMA_STATUS_COLOR: Record<string, string> = {
  missing: "rgba(232, 154, 160, 0.6)",
  broken: "var(--neg)",
  valid_incomplete: "#d4a017",
  valid_complete: "var(--pos)",
};

export function PagesTable({ rows, gaps }: PagesTableProps) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const gridTemplate = "2.2fr 0.8fr 1.6fr 1.4fr 0.7fr";

  return (
    <div>
      <div
        className="grid px-4 pb-3 border-b"
        style={{ gridTemplateColumns: gridTemplate, gap: 12, borderColor: "var(--hair)" }}
      >
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          PAGE
        </div>
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          READINESS
        </div>
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          STRUCTURE
        </div>
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          QUERIES
        </div>
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          WORDS
        </div>
      </div>

      {rows.map((row) => {
        const isExpanded = expanded === row.url;
        return (
          <div key={row.url}>
            <div
              onClick={() => setExpanded(isExpanded ? null : row.url)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  if (e.key === " ") e.preventDefault();
                  setExpanded(isExpanded ? null : row.url);
                }
              }}
              className="grid items-center px-4 py-3 border-b cursor-pointer transition-colors"
              style={{
                gridTemplateColumns: gridTemplate,
                gap: 12,
                borderColor: "var(--hair)",
                background: isExpanded ? "rgba(245,244,241,0.03)" : "transparent",
              }}
            >
              <div>
                <div className="font-serif text-[13px]" style={{ color: "var(--white)" }}>
                  {row.title}
                </div>
                <div className="font-mono text-[9px] mt-0.5" style={{ color: "var(--mute)" }}>
                  {pagePathname(row.url)}
                </div>
              </div>

              <div>
                {row.score === null ? (
                  <span className="font-serif italic text-[12px]" style={{ color: "var(--faint)" }}>
                    not scored
                  </span>
                ) : (
                  <span className="font-mono text-[13px]" style={{ color: readinessColor(row.score) }}>
                    {row.score}/100
                  </span>
                )}
              </div>

              <div className="flex flex-wrap gap-1">
                {row.schemaStatus && (
                  <span
                    className="font-mono text-[8px] tracking-[0.08em] uppercase px-1.5 py-0.5"
                    style={{
                      color: SCHEMA_STATUS_COLOR[row.schemaStatus] ?? "var(--mute)",
                      border: `1px solid ${SCHEMA_STATUS_COLOR[row.schemaStatus] ?? "var(--mute)"}`,
                    }}
                  >
                    {row.schemaStatus.replace(/_/g, " ")}
                  </span>
                )}
                {row.hasFaq && (
                  <span
                    className="font-mono text-[8px] tracking-[0.08em] uppercase px-1.5 py-0.5"
                    style={{ color: "var(--mute)", border: "1px solid var(--hair)" }}
                  >
                    FAQ
                  </span>
                )}
                {row.hasComparison && (
                  <span
                    className="font-mono text-[8px] tracking-[0.08em] uppercase px-1.5 py-0.5"
                    style={{ color: "var(--mute)", border: "1px solid var(--hair)" }}
                  >
                    TABLE
                  </span>
                )}
              </div>

              <div className="font-mono text-[10px]" style={{ color: "var(--mute)" }}>
                {row.queriesServed.length === 0 ? "—" : `${row.queriesServed.length} served`}
              </div>

              <div className="font-mono text-[10px]" style={{ color: "var(--mute)" }}>
                {row.wordCount.toLocaleString()}
              </div>
            </div>

            {isExpanded && (
              <div className="px-4 py-4" style={{ background: "var(--ink-soft)" }}>
                <div className="mb-4">
                  <div
                    className="font-mono text-[9px] tracking-[0.18em] uppercase mb-2"
                    style={{ color: "var(--faint)" }}
                  >
                    STRUCTURAL CHECKS
                  </div>
                  {row.checks === null ? (
                    <p className="font-serif italic text-[12px]" style={{ color: "var(--faint)" }}>
                      not scored — no matched query
                    </p>
                  ) : (
                    <div>
                      {CHECK_ORDER.filter((key) => row.checks && key in row.checks).map((key) => {
                        const check = row.checks![key];
                        return (
                          <div
                            key={key}
                            className="flex items-baseline justify-between py-1.5 border-b"
                            style={{ borderColor: "var(--hair)" }}
                          >
                            <span
                              className="font-mono text-[9px] tracking-[0.06em] uppercase"
                              style={{ color: "var(--mute)" }}
                            >
                              {checkLabel(key)}
                            </span>
                            <span className="font-mono text-[10px]" style={{ color: "var(--white)" }}>
                              {check.score} pts
                              {check.detail && (
                                <span
                                  className="font-serif not-italic text-[12px] ml-2"
                                  style={{ color: "var(--faint)" }}
                                >
                                  {check.detail}
                                </span>
                              )}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {row.schemaErrors.length > 0 && (
                    <div className="mt-2">
                      {row.schemaErrors.map((err, i) => (
                        <div key={i} className="font-mono text-[9px]" style={{ color: "var(--neg)" }}>
                          {err}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {row.sonnet && (
                  <div className="mb-4">
                    <div
                      className="font-mono text-[9px] tracking-[0.18em] uppercase mb-2"
                      style={{ color: "var(--faint)" }}
                    >
                      SONNET QUALITY
                    </div>
                    <div className="font-mono text-[10px]" style={{ color: "var(--white)" }}>
                      SPECIFICITY {row.sonnet.specificity}/5 · COMPLETENESS {row.sonnet.completeness}/5 · DIRECTNESS{" "}
                      {row.sonnet.answer_directness}/5
                    </div>
                    <p className="font-serif italic text-[12px] mt-1" style={{ color: "var(--mute)" }}>
                      {row.sonnet.summary}
                    </p>
                  </div>
                )}

                {row.queriesServed.length > 0 && (
                  <div className="mb-4">
                    <div
                      className="font-mono text-[9px] tracking-[0.18em] uppercase mb-2"
                      style={{ color: "var(--faint)" }}
                    >
                      QUERIES SERVED
                    </div>
                    {row.queriesServed.map((q, i) => (
                      <div key={i} className="flex items-center gap-2 py-1">
                        <span className="font-serif text-[12px]" style={{ color: "var(--white)" }}>
                          &ldquo;{q.query}&rdquo; {q.similarity.toFixed(2)}
                        </span>
                        {q.weak && (
                          <span
                            className="font-mono text-[8px] tracking-[0.08em] px-1.5 py-0.5"
                            style={{ color: "#d4a017", border: "1px solid #d4a017" }}
                          >
                            weak match, not scored
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {row.waitingCards.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {row.waitingCards.map((card) => (
                      <Link
                        key={card.id}
                        href="/admin/approvals"
                        onClick={(e) => e.stopPropagation()}
                        className="font-mono text-[8px] tracking-[0.08em] uppercase px-1.5 py-0.5"
                        style={{ color: "#d4a017", border: "1px solid #d4a017" }}
                      >
                        {card.action_type} WAITING
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}

      {gaps.length > 0 && (
        <div className="mt-8">
          <div className="font-mono text-[9px] tracking-[0.18em] uppercase mb-3" style={{ color: "var(--faint)" }}>
            CONTENT GAPS
          </div>
          {gaps.map((gap, i) => (
            <div
              key={i}
              className="flex items-center justify-between py-3 px-4 border-b"
              style={{ borderColor: "var(--hair)" }}
            >
              <div>
                <div className="font-serif text-[13px]" style={{ color: "var(--white)" }}>
                  {gap.query}
                </div>
                {/* content_gap classification is about match failure, not mention
                    performance — gap can be negative; only show "leads by" when
                    the competitor is actually ahead */}
                {gap.topCompetitor && gap.gap !== null && gap.gap > 0 && (
                  <div className="font-serif text-[12px] mt-0.5" style={{ color: "var(--neg)" }}>
                    {gap.topCompetitor} leads by {formatRate(gap.gap)}
                  </div>
                )}
              </div>
              <div>
                {gap.briefCardId ? (
                  <Link
                    href={`/admin/approvals#card-${gap.briefCardId}`}
                    className="font-mono text-[9px] tracking-[0.08em] uppercase px-2 py-1"
                    style={{ color: "#d4a017", border: "1px solid #d4a017" }}
                  >
                    VIEW BRIEF CARD →
                  </Link>
                ) : (
                  <span className="font-serif italic text-[12px]" style={{ color: "var(--faint)" }}>
                    no brief — generated when a competitor leads
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
