"use client";

import { useState } from "react";
import Link from "next/link";
import { scoreColor, formatRate, getMentionLevelLabel, getMentionLevelColor } from "@/lib/utils";
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

function StatusBadge({ result }: { result: TrackerResult }) {
  if (!result.brand_mentioned && !result.brand_cited) {
    return <span className="font-mono text-[8px] shrink-0" style={{ color: "var(--faint)" }}>not found</span>;
  }

  const label = result.mention_level_label
    ? result.mention_level_label.replace(/_/g, " ").toUpperCase()
    : result.brand_cited
      ? "CITED"
      : "MENTIONED";

  const isCited = result.brand_cited;

  return (
    <span
      className="font-mono text-[8px] tracking-[0.1em] py-0.5 px-2 shrink-0"
      style={{
        color: "var(--pos)",
        border: `1px solid rgba(132,216,171,${isCited ? "0.3" : "0.2"})`,
        background: `rgba(132,216,171,${isCited ? "0.08" : "0.05"})`,
      }}
    >
      {label}
    </span>
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
    const scores = run.per_engine_scores[eng];
    const engineResults = results.filter((r) => r.engine === eng);
    const total = engineResults.length;
    if (!scores) return { engine: eng, mentionRate: 0, avgLevel: 0, citationRate: 0, total };
    return {
      engine: eng,
      mentionRate: scores.mention_rate,
      avgLevel: scores.avg_mention_level,
      citationRate: scores.citation_rate,
      total,
    };
  });

  // All forms the brand might appear in responses (brand_name, name, variations)
  const brandTerms: string[] = [
    client.brand_name,
    client.name,
    ...(client.brand_variations || []),
  ].filter(Boolean).map((t) => t.toLowerCase());

  // Match by exact string OR by stripping spaces from both sides (handles "budgetyourmd" ↔ "Budget Your MD")
  const isClientBrand = (name: string): boolean => {
    const nameLower = name.toLowerCase();
    const nameNorm = nameLower.replace(/\s+/g, "");
    return brandTerms.some(
      (term) => nameLower === term || nameNorm === term.replace(/\s+/g, "")
    );
  };

  const compCounts: Record<string, number> = {};
  results.forEach((r) => {
    r.competitor_mentions.forEach((c) => {
      if (!isClientBrand(c)) {
        compCounts[c] = (compCounts[c] || 0) + 1;
      }
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
          const mentionedCount = results.filter((r) => r.brand_mentioned || r.brand_cited).length;
          const avgLevel = run.aggregate_avg_mention_level ?? 0;
          const topComp = Object.entries(compCounts).sort((a, b) => b[1] - a[1])[0];
          const topCompRate = topComp ? Math.round((topComp[1] / results.length) * 100) + "%" : "-";
          const topCompLabel = topComp ? `${topComp[0]}` : "none detected";
          return [
            { n: formatRate(run.aggregate_mention_rate), l: "Mention Rate", d: `${mentionedCount} of ${results.length}`, color: scoreColor(run.aggregate_mention_rate) },
            { n: avgLevel.toFixed(1), l: "Avg Mention Level", d: getMentionLevelLabel(Math.round(avgLevel)), color: getMentionLevelColor(avgLevel) },
            { n: topCompRate, l: "Top Competitor Rate", d: topCompLabel, color: "var(--mute)" },
            { n: String(Object.keys(run.per_engine_scores).length), l: "Engines", d: "tracked", color: "var(--faint)" },
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
        {engineStats.map(({ engine, mentionRate, avgLevel, citationRate, total }) => (
          <div key={engine} className="p-4 border" style={{ borderColor: "var(--hair)" }}>
            <div className="font-mono text-[10px] tracking-[0.12em] mb-3 font-medium" style={{ color: "var(--white)" }}>
              {ENGINE_LABELS[engine]}
            </div>
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between items-center">
                <span className="font-mono text-[7px] tracking-[0.08em]" style={{ color: "var(--faint)" }}>MENTION</span>
                <span className="font-mono text-[13px] font-medium" style={{ color: scoreColor(mentionRate) }}>
                  {formatRate(mentionRate)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-mono text-[7px] tracking-[0.08em]" style={{ color: "var(--faint)" }}>LEVEL</span>
                <span className="font-mono text-[13px] font-medium" style={{ color: getMentionLevelColor(avgLevel) }}>
                  {avgLevel.toFixed(1)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-mono text-[7px] tracking-[0.08em]" style={{ color: "var(--faint)" }}>CITATION</span>
                <span className="font-mono text-[11px]" style={{ color: "var(--faint)" }}>
                  {formatRate(citationRate)}
                </span>
              </div>
            </div>
          </div>
        ))}
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
                  <td key={eng} style={{ padding: "11px 12px", textAlign: "center", color: "var(--faint)", fontSize: 7 }}>N/A</td>
                );
                if (!r.brand_mentioned && !r.brand_cited) return (
                  <td key={eng} style={{ padding: "11px 12px", textAlign: "center", color: "var(--faint)" }}>-</td>
                );
                const levelShort = r.mention_level === 4 ? "P" : r.mention_level === 3 ? "R" : r.mention_level === 2 ? "L" : "m";
                const color = r.brand_cited ? "var(--pos)" : "rgba(132,216,171,0.8)";
                return (
                  <td key={eng} style={{ padding: "11px 12px", textAlign: "center", color, fontWeight: r.mention_level >= 3 ? 600 : 500, fontSize: 10 }}>
                    {levelShort}{r.brand_cited ? "·C" : ""}
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
                            <ExpandedEngineRow key={r.id} result={r} brandTerms={brandTerms} />
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
          P = primary &nbsp;·&nbsp; R = recommended &nbsp;·&nbsp; L = listed &nbsp;·&nbsp; m = passing &nbsp;·&nbsp; C = cited &nbsp;·&nbsp; - = not found
        </div>
      </div>
    </div>
  );
}

function lineMatchesBrand(line: string, brandTerms: string[]): boolean {
  const lineLower = line.toLowerCase();
  const lineNorm = lineLower.replace(/\s+/g, "");
  return brandTerms.some((term) => {
    // Exact substring: catches "Budget Your MD" when term is "budget your md"
    if (lineLower.includes(term)) return true;
    // Space-stripped: catches "Budget Your MD" when term is "budgetyourmd"
    const termNorm = term.replace(/\s+/g, "");
    return termNorm.length > 2 && lineNorm.includes(termNorm);
  });
}

function SpotlightText({
  text,
  brandTerms,
  open,
  onToggle,
}: {
  text: string;
  brandTerms: string[];
  open: boolean;
  onToggle: (e: React.MouseEvent) => void;
}) {
  const allLines = text.split(/\n/).filter((l) => l.trim().length > 0);

  // Preview: accumulate lines until ~340 chars
  const previewLines: string[] = [];
  let chars = 0;
  for (const line of allLines) {
    previewLines.push(line);
    chars += line.length;
    if (chars >= 340) break;
  }

  const displayLines = open ? allLines : previewLines;
  const hasMore = previewLines.length < allLines.length;

  return (
    <div>
      <div className="flex flex-col gap-[3px]">
        {displayLines.map((line, i) => {
          const isMatch = lineMatchesBrand(line, brandTerms);
          return (
            <div
              key={i}
              style={{
                fontFamily: "var(--mono)",
                fontSize: 10,
                lineHeight: "1.65",
                color: isMatch ? "var(--mute)" : "rgba(245,244,241,0.16)",
                borderLeft: `2px solid ${isMatch ? "rgba(132,216,171,0.5)" : "transparent"}`,
                paddingLeft: 8,
                wordBreak: "break-word",
              }}
            >
              {line}
            </div>
          );
        })}
      </div>
      {hasMore && (
        <button
          onClick={onToggle}
          className="font-mono text-[8px] tracking-[0.1em] uppercase mt-2 transition-colors hover:text-white"
          style={{ color: "var(--faint)" }}
        >
          {open ? "collapse" : "read full"}
        </button>
      )}
    </div>
  );
}

function ExpandedEngineRow({ result, brandTerms }: { result: TrackerResult; brandTerms: string[] }) {
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
          <StatusBadge result={result} />
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
          <SpotlightText
            text={result.response_text}
            brandTerms={brandTerms}
            open={open}
            onToggle={(e) => { e.stopPropagation(); setOpen(!open); }}
          />
        )}
      </div>
    </div>
  );
}
