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
      style={{ color: "var(--pos)", border: "1px solid rgba(132,216,171,0.2)", background: "rgba(132,216,171,0.05)" }}
    >
      MENTIONED
    </span>
  );
  return (
    <span className="font-mono text-[8px] shrink-0" style={{ color: "var(--faint)" }}>not found</span>
  );
}

function SectionDivider({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="font-mono text-[10px] tracking-[0.18em] uppercase pb-3 mb-5 border-b font-medium"
      style={{ color: "var(--white)", borderColor: "var(--hair)", marginTop: 44 }}
    >
      {children}
    </div>
  );
}

export function RunDetail({ run, results, client, clientId }: RunDetailProps) {
  const [expandedQuery, setExpandedQuery] = useState<string | null>(null);

  const queries = Array.from(new Set(results.map((r) => r.query)));
  const byQuery = (q: string) => results.filter((r) => r.query === q);

  const engineStats = ENGINES.map((eng) => {
    const engineResults = results.filter((r) => r.engine === eng);
    const cited = engineResults.filter((r) => r.brand_cited).length;
    const mentioned = engineResults.filter((r) => r.brand_mentioned && !r.brand_cited).length;
    const total = engineResults.length;
    return { engine: eng, cited, mentioned, notFound: total - cited - mentioned, total };
  });

  const compCounts: Record<string, number> = {};
  results.forEach((r) => {
    r.competitor_mentions.forEach((c) => {
      compCounts[c] = (compCounts[c] || 0) + 1;
    });
  });
  const competitors = Object.entries(compCounts).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const maxCompMentions = competitors[0]?.[1] ?? 1;

  const citationsByUrl: Record<string, string[]> = {};
  results
    .filter((r) => r.brand_cited && r.citation_url)
    .forEach((r) => {
      const url = r.citation_url!;
      if (!citationsByUrl[url]) citationsByUrl[url] = [];
      citationsByUrl[url].push(ENGINE_LABELS[r.engine] ?? r.engine);
    });

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
          MAKE REPORT
        </Link>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-4 mb-10" style={{ gap: 1, background: "var(--hair)", border: "1px solid var(--hair)" }}>
        {(() => {
          const citedCount = results.filter((r) => r.brand_cited).length;
          const topComp = Object.entries(compCounts).sort((a, b) => b[1] - a[1])[0];
          const topCompRate = topComp ? Math.round((topComp[1] / results.length) * 100) + "%" : "-";
          const topCompLabel = topComp ? `${topComp[0]}` : "none detected";
          const mentionedCount = results.filter((r) => r.brand_mentioned || r.brand_cited).length;
          return [
            { n: formatRate(run.aggregate_mention_rate), l: "Mention Rate", d: `${mentionedCount} of ${results.length}`, color: scoreColor(run.aggregate_mention_rate) },
            { n: formatRate(run.aggregate_citation_rate), l: "Citation Rate", d: `${citedCount} URL${citedCount !== 1 ? "s" : ""} cited`, color: scoreColor(run.aggregate_citation_rate) },
            { n: topCompRate, l: "Top Competitor Rate", d: topCompLabel, color: "var(--mute)" },
            { n: String(citedCount), l: "Citations Found", d: `across ${results.filter(r=>r.brand_cited).map(r=>r.engine).filter((v,i,a)=>a.indexOf(v)===i).length} engine${results.filter(r=>r.brand_cited).map(r=>r.engine).filter((v,i,a)=>a.indexOf(v)===i).length!==1?"s":""}`, color: "var(--faint)" },
          ];
        })().map(({ n, l, d, color }) => (
          <div key={l} className="py-5 px-5" style={{ background: "var(--ink)" }}>
            <div className="font-display text-[44px] font-light leading-none mb-2" style={{ color }}>{n}</div>
            <div className="font-mono text-[9px] tracking-[0.1em] mb-0.5" style={{ color: "var(--mute)" }}>{l}</div>
            <div className="font-mono text-[8px]" style={{ color: "var(--faint)" }}>{d}</div>
          </div>
        ))}
      </div>

      {/* Per-engine breakdown */}
      <SectionDivider>
        Per-Engine Breakdown{" "}
        <span style={{ fontSize: 8, letterSpacing: "0.06em", opacity: 0.5, fontWeight: 400, marginLeft: 10 }}>
          {Math.round(results.length / ENGINES.length)} queries each
        </span>
      </SectionDivider>
      <div className="grid grid-cols-4 gap-3 mb-2">
        {engineStats.map(({ engine, cited, mentioned, notFound, total }) => {
          const citedPct = total > 0 ? (cited / total) * 100 : 0;
          const mentionedPct = total > 0 ? (mentioned / total) * 100 : 0;
          return (
            <div key={engine} className="p-4 border" style={{ borderColor: "var(--hair)" }}>
              <div className="font-mono text-[10px] tracking-[0.12em] mb-3 font-medium" style={{ color: "var(--white)" }}>
                {ENGINE_LABELS[engine]}
              </div>
              <div className="flex h-1 mb-3 overflow-hidden" style={{ background: "var(--hair)" }}>
                <div style={{ width: `${citedPct}%`, background: "var(--pos)" }} />
                <div style={{ width: `${mentionedPct}%`, background: "rgba(132,216,171,0.35)" }} />
              </div>
              <div className="flex flex-col gap-1.5">
                {[
                  { label: "CITED", val: cited, color: "var(--pos)" },
                  { label: "MENTIONED", val: mentioned, color: "rgba(132,216,171,0.7)" },
                  { label: "NOT FOUND", val: notFound, color: "var(--faint)" },
                ].map(({ label, val, color }) => (
                  <div key={label} className="flex justify-between items-center">
                    <span className="font-mono text-[7px] tracking-[0.08em]" style={{ color }}>
                      {label}
                    </span>
                    <span className="font-mono text-[11px] font-medium" style={{ color: val > 0 ? "var(--white)" : "var(--faint)" }}>
                      {val}
                      <span style={{ opacity: 0.35, fontSize: 8 }}>/{total}</span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Competitor SoV */}
      <SectionDivider>Competitor Share of Voice</SectionDivider>
      <table className="w-full border-collapse mb-2">
        <thead>
          <tr className="border-b" style={{ borderColor: "var(--hair)" }}>
            {["Brand", "Rate"].map((h) => (
              <th
                key={h}
                className="font-mono text-[9px] tracking-[0.1em] uppercase pb-2.5 text-left font-normal"
                style={{ color: "var(--faint)" }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr className="border-b" style={{ borderColor: "var(--hair)" }}>
            <td className="py-2.5 font-serif text-sm" style={{ color: "var(--pos)" }}>
              {client.brand_name}
              <span className="font-mono text-[7px] tracking-[0.08em] ml-2 opacity-60">YOUR BRAND</span>
            </td>
            <td className="py-2.5 font-mono text-[13px] font-medium" style={{ color: "var(--pos)" }}>
              {formatRate(run.aggregate_mention_rate)}
            </td>
          </tr>
          {competitors.map(([name, count]) => (
            <tr key={name} className="border-b" style={{ borderColor: "var(--hair)" }}>
              <td className="py-2.5 font-serif text-sm" style={{ color: "var(--mute)" }}>{name}</td>
              <td className="py-2.5 font-mono text-[13px]" style={{ color: "var(--faint)" }}>
                {Math.round((count / results.length) * 100)}%
              </td>
            </tr>
          ))}
          {competitors.length === 0 && (
            <tr>
              <td colSpan={2} className="py-4 font-mono text-[9px]" style={{ color: "var(--faint)" }}>
                No competitor mentions detected this run.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {/* Citation URLs */}
      <SectionDivider>Citation URLs</SectionDivider>
      {Object.keys(citationsByUrl).length === 0 ? (
        <p className="font-mono text-[9px]" style={{ color: "var(--faint)" }}>No URLs cited this run.</p>
      ) : (
        <div className="flex flex-col gap-0">
          {Object.entries(citationsByUrl).map(([url, engines]) => (
            <div
              key={url}
              className="flex items-baseline gap-6 py-3 border-b"
              style={{ borderColor: "var(--hair)" }}
            >
              <a
                href={url.startsWith("http") ? url : `https://${url}`}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-[10px] tracking-[0.04em] hover:opacity-70 transition-opacity flex-1 min-w-0 break-all"
                style={{ color: "var(--white)" }}
              >
                {url}
              </a>
              <span className="font-mono text-[8px] shrink-0" style={{ color: "var(--faint)" }}>
                {engines.join(" · ")}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Query matrix — clickable rows expand to show excerpts */}
      <SectionDivider>
        Query Results{" "}
        <span style={{ fontSize: 8, letterSpacing: "0.06em", opacity: 0.5, fontWeight: 400, marginLeft: 8 }}>
          {queries.length} {queries.length !== 1 ? "queries" : "query"} · click any row to expand
        </span>
      </SectionDivider>
      <div className="overflow-x-auto">
        <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "var(--mono)", fontSize: 9 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: "8px 12px 8px 0", color: "var(--faint)", fontWeight: 400, borderBottom: "1px solid var(--hair)" }}>
                QUERY
              </th>
              {["GPT", "PERP", "CLAUDE", "GEMINI"].map((e) => (
                <th key={e} style={{ padding: "8px 12px", color: "var(--faint)", fontWeight: 400, borderBottom: "1px solid var(--hair)", textAlign: "center" }}>
                  {e}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {queries.map((query) => {
              const qResults = byQuery(query);
              const isExpanded = expandedQuery === query;
              const cellFor = (eng: string) => {
                const r = qResults.find((r) => r.engine === eng);
                if (!r) return (
                  <td key={eng} style={{ padding: "11px 12px", textAlign: "center", color: "var(--faint)", fontSize: 7 }}>
                    N/A
                  </td>
                );
                if (r.brand_cited) return (
                  <td key={eng} style={{ padding: "11px 12px", textAlign: "center", color: "var(--pos)", fontWeight: 600, fontSize: 10 }}>
                    C
                  </td>
                );
                if (r.brand_mentioned) return (
                  <td key={eng} style={{ padding: "11px 12px", textAlign: "center", color: "rgba(132,216,171,0.8)", fontWeight: 500 }}>
                    M
                  </td>
                );
                return (
                  <td key={eng} style={{ padding: "11px 12px", textAlign: "center", color: "var(--faint)" }}>
                    -
                  </td>
                );
              };

              return (
                <>
                  <tr
                    key={query}
                    onClick={() => setExpandedQuery(isExpanded ? null : query)}
                    style={{
                      borderBottom: "1px solid var(--hair)",
                      cursor: "pointer",
                      background: isExpanded ? "rgba(245,244,241,0.03)" : "transparent",
                    }}
                    className="hover:bg-[rgba(245,244,241,0.025)] transition-colors"
                  >
                    <td style={{ padding: "11px 12px 11px 0", color: isExpanded ? "var(--white)" : "var(--mute)" }}>
                      {query}
                      {isExpanded && (
                        <span style={{ color: "var(--faint)", marginLeft: 6, fontSize: 8 }}>↑ collapse</span>
                      )}
                    </td>
                    {["chatgpt", "perplexity", "claude", "gemini"].map((eng) => cellFor(eng))}
                  </tr>
                  {isExpanded && (
                    <tr key={`${query}-expanded`} style={{ borderBottom: "1px solid var(--hair)" }}>
                      <td colSpan={5} style={{ padding: "0 0 12px 0", background: "rgba(245,244,241,0.02)" }}>
                        <div className="flex flex-col gap-0 pt-1">
                          {qResults.map((r) => (
                            <ExpandedEngineRow key={r.id} result={r} />
                          ))}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
        <div className="font-mono mt-2" style={{ fontSize: 8, color: "var(--faint)", letterSpacing: "0.06em" }}>
          M = mentioned &nbsp;·&nbsp; C = cited &nbsp;·&nbsp; - = not found &nbsp;·&nbsp; N/A = skipped
        </div>
      </div>
    </div>
  );
}

function ExpandedEngineRow({ result }: { result: TrackerResult }) {
  const PREVIEW_LEN = 340;
  const [open, setOpen] = useState(false);
  const hasText = result.response_text && result.response_text.length > 0;
  const showable = (result.brand_mentioned || result.brand_cited) && hasText;

  return (
    <div
      className="flex gap-4 py-2.5 border-b"
      style={{ borderColor: "var(--hair)", paddingLeft: 0 }}
    >
      <span
        className="font-mono text-[8px] tracking-[0.1em] w-24 shrink-0 pt-0.5"
        style={{ color: "var(--mute)" }}
      >
        {ENGINE_LABELS[result.engine] ?? result.engine.toUpperCase()}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 mb-1.5 flex-wrap">
          <StatusBadge mentioned={result.brand_mentioned} cited={result.brand_cited} />
          {result.citation_url && (
            <a
              href={result.citation_url.startsWith("http") ? result.citation_url : `https://${result.citation_url}`}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-[8px] tracking-[0.06em] truncate max-w-[260px] hover:opacity-70 transition-opacity"
              style={{ color: "var(--pos)" }}
            >
              {result.citation_url}
            </a>
          )}
        </div>
        {showable && (
          <div>
            <p
              className="font-mono text-[10px] leading-relaxed whitespace-pre-wrap break-words"
              style={{ color: "var(--mute)" }}
            >
              {open
                ? result.response_text
                : result.response_text.slice(0, PREVIEW_LEN) +
                  (result.response_text.length > PREVIEW_LEN ? "..." : "")}
            </p>
            {result.response_text.length > PREVIEW_LEN && (
              <button
                onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
                className="font-mono text-[8px] tracking-[0.1em] uppercase mt-1.5 transition-colors hover:text-white"
                style={{ color: "var(--faint)" }}
              >
                {open ? "collapse" : "read full"}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
