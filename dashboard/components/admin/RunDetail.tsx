"use client";

import { useState } from "react";
import Link from "next/link";
import { scoreColor, formatRate } from "@/lib/utils";
import type { TrackerRun, TrackerResult, Client } from "@/lib/types";

interface RunDetailProps {
  run: TrackerRun;
  results: TrackerResult[];
  client: Client;
  clientId: string;
}

const ENGINES = ["chatgpt", "perplexity", "claude", "gemini"];
const ENGINE_LABELS: Record<string, string> = {
  chatgpt: "CHATGPT",
  perplexity: "PERPLEXITY",
  claude: "CLAUDE",
  gemini: "GEMINI",
};

// Badge shown on each result row
function StatusBadge({ mentioned, cited }: { mentioned: boolean; cited: boolean }) {
  if (cited) return (
    <span
      className="font-mono text-[8px] tracking-[0.1em] py-0.5 px-2 shrink-0"
      style={{ color: "var(--pos)", border: "1px solid rgba(132,216,171,0.3)", background: "rgba(132,216,171,0.08)" }}
    >
      CITED
    </span>
  );
  if (mentioned) return (
    <span
      className="font-mono text-[8px] tracking-[0.1em] py-0.5 px-2 shrink-0"
      style={{ color: "var(--mute)", border: "1px solid var(--ghost)" }}
    >
      MENTIONED
    </span>
  );
  return (
    <span className="font-mono text-[8px] shrink-0" style={{ color: "var(--faint)" }}>— not found</span>
  );
}

// Expandable result row for one engine within a query
function ResultRow({ result }: { result: TrackerResult }) {
  const [open, setOpen] = useState(false);
  const PREVIEW_LEN = 320;
  const hasText = result.response_text && result.response_text.length > 0;
  const showable = (result.brand_mentioned || result.brand_cited) && hasText;

  return (
    <div className="flex gap-4 py-3 border-b last:border-b-0" style={{ borderColor: "var(--hair)" }}>
      <span className="font-mono text-[9px] tracking-[0.1em] w-24 shrink-0 pt-0.5" style={{ color: "var(--mute)" }}>
        {ENGINE_LABELS[result.engine] ?? result.engine.toUpperCase()}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 mb-1.5 flex-wrap">
          <StatusBadge mentioned={result.brand_mentioned} cited={result.brand_cited} />
          {result.citation_url && (
            <span className="font-mono text-[8px] tracking-[0.06em] truncate max-w-[260px]" style={{ color: "var(--pos)" }}>
              ↗ {result.citation_url}
            </span>
          )}
        </div>
        {showable && (
          <div>
            <p className="font-mono text-[10px] leading-relaxed whitespace-pre-wrap break-words" style={{ color: "var(--mute)" }}>
              {open
                ? result.response_text
                : result.response_text.slice(0, PREVIEW_LEN) + (result.response_text.length > PREVIEW_LEN ? "…" : "")}
            </p>
            {result.response_text.length > PREVIEW_LEN && (
              <button
                onClick={() => setOpen(!open)}
                className="font-mono text-[8px] tracking-[0.1em] uppercase mt-1.5 transition-colors hover:text-white"
                style={{ color: "var(--faint)" }}
              >
                {open ? "↑ collapse" : "··· read full"}
              </button>
            )}
          </div>
        )}
        {result.competitor_mentions.length > 0 && (
          <p className="font-mono text-[8px] mt-1.5 opacity-50" style={{ color: "var(--faint)" }}>
            competitors: {result.competitor_mentions.join(", ")}
          </p>
        )}
      </div>
    </div>
  );
}

export function RunDetail({ run, results, client, clientId }: RunDetailProps) {
  const [showAll, setShowAll] = useState(false);
  const INITIAL_VISIBLE = 3;

  // Group results by query, preserve order
  const queries = Array.from(new Set(results.map((r) => r.query)));
  const byQuery = (q: string) => results.filter((r) => r.query === q);

  // Per-engine breakdown computed from results
  const engineStats = ENGINES.map((eng) => {
    const engineResults = results.filter((r) => r.engine === eng);
    const cited = engineResults.filter((r) => r.brand_cited).length;
    const mentioned = engineResults.filter((r) => r.brand_mentioned && !r.brand_cited).length;
    const total = engineResults.length;
    return { engine: eng, cited, mentioned, notFound: total - cited - mentioned, total };
  });

  // Competitor SoV from results
  const compCounts: Record<string, number> = {};
  results.forEach((r) => {
    r.competitor_mentions.forEach((c) => {
      compCounts[c] = (compCounts[c] || 0) + 1;
    });
  });
  const competitors = Object.entries(compCounts).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const maxCompMentions = competitors[0]?.[1] ?? 1;

  // Citation URLs
  const citationsByUrl: Record<string, string[]> = {};
  results
    .filter((r) => r.brand_cited && r.citation_url)
    .forEach((r) => {
      const url = r.citation_url!;
      if (!citationsByUrl[url]) citationsByUrl[url] = [];
      citationsByUrl[url].push(ENGINE_LABELS[r.engine] ?? r.engine);
    });

  const visibleQueries = showAll ? queries : queries.slice(0, INITIAL_VISIBLE);
  const hiddenCount = queries.length - INITIAL_VISIBLE;

  return (
    <div style={{ maxWidth: 960 }}>
      {/* Header */}
      <div className="flex items-end justify-between mb-8 flex-wrap gap-4">
        <div>
          <h2
            className="font-display text-[clamp(28px,4vw,44px)] font-light leading-[1.02]"
            style={{ color: "var(--white)" }}
          >
            {new Date(run.ran_at).toLocaleDateString("en-US", {
              month: "long",
              day: "numeric",
              year: "numeric",
            })}
          </h2>
          <p className="font-mono text-[9px] tracking-[0.1em] mt-1.5" style={{ color: "var(--faint)" }}>
            {new Date(run.ran_at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}
            {" · "}{results.length} response{results.length !== 1 ? "s" : ""}
          </p>
        </div>
        <Link
          href={`/api/admin/create-report?runId=${run.id}&clientId=${clientId}`}
          className="font-mono text-[9px] tracking-[0.14em] uppercase py-3 px-5 transition-all duration-200 hover:bg-white hover:text-[var(--ink)]"
          style={{ color: "var(--white)", border: "1px solid var(--ghost)" }}
        >
          → MAKE REPORT
        </Link>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-4 mb-10" style={{ gap: 1, background: "var(--hair)" }}>
        {[
          { n: formatRate(run.aggregate_mention_rate), l: "MENTION RATE", color: scoreColor(run.aggregate_mention_rate) },
          { n: formatRate(run.aggregate_citation_rate), l: "CITATION RATE", color: scoreColor(run.aggregate_citation_rate) },
          { n: String(results.length), l: "RESPONSES", color: "var(--mute)" },
          { n: String(results.filter((r) => r.brand_cited).length), l: "CITATIONS", color: "var(--mute)" },
        ].map(({ n, l, color }) => (
          <div key={l} className="py-5 px-5" style={{ background: "var(--ink)" }}>
            <div className="font-display text-[40px] font-light leading-none mb-2" style={{ color }}>{n}</div>
            <div className="font-mono text-[8px] tracking-[0.14em]" style={{ color: "var(--faint)" }}>{l}</div>
          </div>
        ))}
      </div>

      {/* Per-engine breakdown */}
      <div className="font-mono text-[8px] tracking-[0.18em] uppercase mb-4" style={{ color: "var(--faint)" }}>
        PER-ENGINE BREAKDOWN
      </div>
      <div className="grid grid-cols-4 gap-3 mb-10">
        {engineStats.map(({ engine, cited, mentioned, notFound, total }) => {
          const citedPct = total > 0 ? (cited / total) * 100 : 0;
          const mentionedPct = total > 0 ? (mentioned / total) * 100 : 0;
          const notFoundPct = total > 0 ? (notFound / total) * 100 : 0;
          return (
            <div key={engine} className="p-4 border" style={{ borderColor: "var(--hair)" }}>
              <div className="font-mono text-[9px] tracking-[0.14em] mb-3" style={{ color: "var(--mute)" }}>
                {ENGINE_LABELS[engine]}
              </div>
              {/* Stacked bar */}
              <div className="flex h-1 mb-3 overflow-hidden" style={{ background: "var(--hair)" }}>
                <div style={{ width: `${citedPct}%`, background: "var(--pos)" }} />
                <div style={{ width: `${mentionedPct}%`, background: "rgba(132,216,171,0.35)" }} />
                <div style={{ width: `${notFoundPct}%`, background: "transparent" }} />
              </div>
              <div className="flex flex-col gap-1.5">
                {[
                  { label: "CITED", val: cited, color: "var(--pos)" },
                  { label: "MENTIONED", val: mentioned, color: "var(--mute)" },
                  { label: "NOT FOUND", val: notFound, color: "var(--faint)" },
                ].map(({ label, val, color }) => (
                  <div key={label} className="flex justify-between items-center">
                    <span className="font-mono text-[7px] tracking-[0.08em]" style={{ color }}>● {label}</span>
                    <span className="font-mono text-[9px]" style={{ color: val > 0 ? "var(--white)" : "var(--faint)" }}>
                      {val}<span style={{ opacity: 0.4 }}>/{total}</span>
                    </span>
                  </div>
                ))}
              </div>
              {total < results.length / ENGINES.length && total > 0 && (
                <div className="font-mono text-[7px] mt-2" style={{ color: "var(--faint)", opacity: 0.5 }}>
                  skipped {Math.round(results.length / ENGINES.length) - total} quer
                  {Math.round(results.length / ENGINES.length) - total === 1 ? "y" : "ies"}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Competitor SoV */}
      <div className="mb-10">
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase mb-4" style={{ color: "var(--faint)" }}>
          COMPETITOR SHARE OF VOICE
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b" style={{ borderColor: "var(--hair)" }}>
              {["BRAND", "APPEARANCES", "RATE"].map((h) => (
                <th
                  key={h}
                  className="font-mono text-[8px] tracking-[0.12em] uppercase pb-2.5 text-left font-normal"
                  style={{ color: "var(--faint)" }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {/* Brand row - always shown */}
            <tr className="border-b" style={{ borderColor: "var(--hair)" }}>
              <td className="py-3 font-serif text-sm" style={{ color: "var(--pos)" }}>{client.brand_name}</td>
              <td className="py-3 pr-8">
                <div
                  className="h-0.5"
                  style={{ width: `${run.aggregate_mention_rate * 200}px`, maxWidth: 200, background: "var(--pos)" }}
                />
              </td>
              <td className="py-3 font-mono text-[10px]" style={{ color: "var(--pos)" }}>
                {formatRate(run.aggregate_mention_rate)}
              </td>
            </tr>
            {/* Competitor rows - only when there are competitors */}
            {competitors.map(([name, count]) => (
              <tr key={name} className="border-b" style={{ borderColor: "var(--hair)" }}>
                <td className="py-3 font-serif text-sm" style={{ color: "var(--mute)" }}>{name}</td>
                <td className="py-3 pr-8">
                  <div
                    className="h-0.5"
                    style={{
                      width: `${(count / maxCompMentions) * 200 * 0.7}px`,
                      maxWidth: 200,
                      background: "var(--ghost)",
                    }}
                  />
                </td>
                <td className="py-3 font-mono text-[10px]" style={{ color: "var(--faint)" }}>
                  {Math.round((count / results.length) * 100)}%
                </td>
              </tr>
            ))}
            {/* Empty state when no competitors */}
            {competitors.length === 0 && (
              <tr>
                <td colSpan={3} className="py-4 font-mono text-[9px]" style={{ color: "var(--faint)" }}>
                  No competitor mentions detected this run.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Citation URLs */}
      <div className="mb-10">
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase mb-4" style={{ color: "var(--faint)" }}>
          CITATION URLS DISCOVERED
        </div>
        {Object.keys(citationsByUrl).length === 0 ? (
          <p className="font-mono text-[9px]" style={{ color: "var(--faint)" }}>No URLs cited this run.</p>
        ) : (
          Object.entries(citationsByUrl).map(([url, engines]) => (
            <div
              key={url}
              className="flex items-center gap-4 py-3 border-b flex-wrap"
              style={{ borderColor: "var(--hair)" }}
            >
              <span className="font-mono text-[10px] tracking-[0.04em] break-all" style={{ color: "var(--white)" }}>
                {url}
              </span>
              <span className="font-mono text-[8px]" style={{ color: "var(--faint)" }}>
                {engines.join(" · ")}
              </span>
              <span className="font-mono text-[8px] ml-auto" style={{ color: "var(--faint)" }}>
                {engines.length} citation{engines.length !== 1 ? "s" : ""}
              </span>
            </div>
          ))
        )}
      </div>

      {/* Query results */}
      <div className="flex items-center justify-between mb-6">
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          QUERY RESULTS
          <span className="ml-3" style={{ opacity: 0.5 }}>
            {queries.length} quer{queries.length !== 1 ? "ies" : "y"} · {results.length} responses
          </span>
        </div>
      </div>

      {visibleQueries.map((query) => (
        <div key={query} className="mb-6 pb-6 border-b" style={{ borderColor: "var(--hair)" }}>
          <div className="font-serif italic text-[15px] mb-3" style={{ color: "var(--mute)" }}>
            &ldquo;{query}&rdquo;
          </div>
          {byQuery(query).every((r) => !r.brand_mentioned) && (
            <div className="font-mono text-[8px] tracking-[0.08em] mb-2" style={{ color: "var(--neg)" }}>
              Zero mentions across all engines
            </div>
          )}
          {byQuery(query).map((result) => (
            <ResultRow key={result.id} result={result} />
          ))}
        </div>
      ))}

      {queries.length > INITIAL_VISIBLE && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="w-full font-mono text-[9px] tracking-[0.14em] uppercase py-4 transition-all duration-200 hover:text-white"
          style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}
        >
          {showAll
            ? "COLLAPSE QUERIES ↑"
            : `SHOW ${hiddenCount} MORE QUER${hiddenCount === 1 ? "Y" : "IES"} ↓`}
        </button>
      )}
    </div>
  );
}
