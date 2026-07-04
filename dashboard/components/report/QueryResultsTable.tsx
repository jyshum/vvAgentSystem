"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import type { TrackerResultClient } from "@/lib/types";

// DB stores engine names lowercase; display labels keyed by lowercase
const ENGINE_DISPLAY: Record<string, string> = {
  chatgpt: "ChatGPT",
  perplexity: "Perplexity",
  claude: "Claude",
  gemini: "Gemini",
};
const ENGINE_ORDER = ["chatgpt", "perplexity", "claude", "gemini"];

interface QueryResultsTableProps {
  results: TrackerResultClient[];
  brandName: string;
  brandVariations: string[];
}

// Build all lowercase search terms from brand name + variations
function buildBrandTerms(brandName: string, brandVariations: string[]): string[] {
  return [brandName, ...brandVariations]
    .filter(Boolean)
    .map((t) => t.toLowerCase());
}

// Match line against brand terms — exact substring OR space-stripped
function lineMatchesBrand(line: string, brandTerms: string[]): boolean {
  const lineLower = line.toLowerCase();
  const lineNorm = lineLower.replace(/\s+/g, "");
  return brandTerms.some((term) => {
    if (lineLower.includes(term)) return true;
    const termNorm = term.replace(/\s+/g, "");
    return termNorm.length > 2 && lineNorm.includes(termNorm);
  });
}

// Extract only the lines/sentences that contain the brand mention
function extractMentionLines(text: string, brandTerms: string[]): string[] {
  return text
    .split(/\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0 && lineMatchesBrand(l, brandTerms));
}

export function QueryResultsTable({ results, brandName, brandVariations }: QueryResultsTableProps) {
  const brandTerms = buildBrandTerms(brandName, brandVariations);

  // Group by query
  const queryMap = new Map<string, TrackerResultClient[]>();
  for (const r of results) {
    const existing = queryMap.get(r.query) ?? [];
    existing.push(r);
    queryMap.set(r.query, existing);
  }

  // Only show queries where at least one engine mentioned or cited the brand
  const mentionQueries = Array.from(queryMap.entries()).filter(([, engineResults]) =>
    engineResults.some((r) => r.brand_mentioned || r.brand_cited)
  );

  if (mentionQueries.length === 0) return null;

  return (
    <div className="mt-[50px]">
      <h2
        className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] mb-6"
        style={{
          color: "var(--p-mute)",
          borderBottom: "1px solid var(--p-hair)",
        }}
      >
        Where Your Brand Was Mentioned
      </h2>

      <div className="flex flex-col gap-0">
        {mentionQueries.map(([query, engineResults], idx) => (
          <QueryBlock
            key={query}
            query={query}
            engineResults={engineResults}
            brandTerms={brandTerms}
            isLast={idx === mentionQueries.length - 1}
          />
        ))}
      </div>
    </div>
  );
}

function QueryBlock({
  query,
  engineResults,
  brandTerms,
  isLast,
}: {
  query: string;
  engineResults: TrackerResultClient[];
  brandTerms: string[];
  isLast: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  // Keyed by lowercase engine name to match DB values
  const byEngine = new Map<string, TrackerResultClient>();
  for (const r of engineResults) {
    byEngine.set(r.engine.toLowerCase(), r);
  }

  // Only show engines that mentioned/cited — "Not Found" rows add no value
  const mentionEngines = ENGINE_ORDER.filter((eng) => {
    const r = byEngine.get(eng);
    return r && (r.brand_mentioned || r.brand_cited);
  });

  const citationUrl = engineResults.find((r) => r.citation_url)?.citation_url;

  return (
    <div
      style={{
        borderBottom: isLast ? "none" : "1px solid var(--p-hair)",
        paddingBottom: "24px",
        marginBottom: "24px",
      }}
    >
      {/* Query */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div
          className="font-serif italic font-light text-[18px] leading-snug flex-1"
          style={{ color: "var(--paper-ink)" }}
        >
          {query}
        </div>
        {mentionEngines.some((eng) => {
          const r = byEngine.get(eng);
          return r?.response_text;
        }) && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="font-mono text-[8px] tracking-[0.14em] uppercase flex-shrink-0 mt-1 transition-opacity hover:opacity-60"
            style={{ color: "var(--p-faint)" }}
          >
            {expanded ? "Hide" : "Show context"}
          </button>
        )}
      </div>

      {/* Engine rows — only mention-positive */}
      <div className="flex flex-col gap-0">
        {mentionEngines.map((eng) => {
          const result = byEngine.get(eng)!;
          return (
            <EngineRow
              key={eng}
              engine={ENGINE_DISPLAY[eng] ?? eng}
              result={result}
              brandTerms={brandTerms}
              expanded={expanded}
            />
          );
        })}
      </div>

      {/* Citation chip */}
      {citationUrl && (
        <div className="mt-3">
          <a
            href={citationUrl.startsWith("http") ? citationUrl : `https://${citationUrl}`}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-[9px] tracking-[0.08em] inline-block px-2.5 py-1 transition-opacity hover:opacity-70"
            style={{
              color: "var(--pos-paper)",
              background: "var(--pos-paper-soft)",
              border: "1px solid var(--pos-paper-border)",
            }}
          >
            {"↗"} {citationUrl.replace(/^https?:\/\//, "")}
          </a>
        </div>
      )}
    </div>
  );
}

function EngineRow({
  engine,
  result,
  brandTerms,
  expanded,
}: {
  engine: string;
  result: TrackerResultClient;
  brandTerms: string[];
  expanded: boolean;
}) {
  const variant = result.brand_cited
    ? "cited-paper"
    : result.brand_mentioned
      ? "mentioned-paper"
      : "not-found-paper";

  const levelLabel = result.mention_level_label
    ? result.mention_level_label.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())
    : result.brand_cited
      ? "Cited"
      : result.brand_mentioned
        ? "Mentioned"
        : "Not Found";

  const label = result.brand_mentioned ? levelLabel : "Not Found";

  const mentionLines =
    result.response_text ? extractMentionLines(result.response_text, brandTerms) : [];

  return (
    <div>
      <div
        className="flex items-center gap-3 py-[7px]"
        style={{ borderBottom: "1px solid var(--p-hair)" }}
      >
        <div
          className="font-mono text-[10px] tracking-[0.1em] uppercase w-[90px] flex-shrink-0"
          style={{ color: "var(--p-faint)" }}
        >
          {engine}
        </div>
        <div className="flex-shrink-0">
          <Badge variant={variant}>{label}</Badge>
        </div>
      </div>

      {expanded && mentionLines.length > 0 && (
        <div className="pt-2 pb-3 flex flex-col gap-[5px]" style={{ borderBottom: "1px solid var(--p-ghost)" }}>
          {mentionLines.map((line, i) => (
            <div
              key={i}
              className="font-serif text-[13px] leading-relaxed"
              style={{
                color: "var(--paper-ink)",
                borderLeft: "2px solid var(--pos-paper-border)",
                paddingLeft: 10,
                opacity: 0.85,
              }}
            >
              {line}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
