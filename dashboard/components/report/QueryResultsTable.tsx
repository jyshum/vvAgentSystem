"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import type { TrackerResultClient } from "@/lib/types";

const ENGINES = ["ChatGPT", "Perplexity", "Claude", "Gemini"];
const DEFAULT_SHOWN = 3;

interface QueryResultsTableProps {
  results: TrackerResultClient[];
}

export function QueryResultsTable({ results }: QueryResultsTableProps) {
  // Group results by query
  const queryMap = new Map<string, TrackerResultClient[]>();
  for (const r of results) {
    const existing = queryMap.get(r.query) ?? [];
    existing.push(r);
    queryMap.set(r.query, existing);
  }
  const queries = Array.from(queryMap.entries());
  const totalQueries = queries.length;

  const [showAll, setShowAll] = useState(false);
  const visibleQueries = showAll ? queries : queries.slice(0, DEFAULT_SHOWN);

  if (queries.length === 0) return null;

  return (
    <div className="mt-[50px]">
      <h2
        className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] mb-6"
        style={{
          color: "var(--p-mute)",
          borderBottom: "1px solid var(--p-hair)",
        }}
      >
        GEO Query Results
      </h2>

      <div className="flex flex-col gap-0">
        {visibleQueries.map(([query, engineResults], idx) => (
          <QueryBlock
            key={query}
            query={query}
            engineResults={engineResults}
            isLast={idx === visibleQueries.length - 1 && (showAll || totalQueries <= DEFAULT_SHOWN)}
          />
        ))}
      </div>

      {!showAll && totalQueries > DEFAULT_SHOWN && (
        <button
          onClick={() => setShowAll(true)}
          className="mt-4 font-mono text-[10px] tracking-[0.12em] uppercase px-4 py-2.5 w-full text-center transition-colors"
          style={{
            color: "var(--p-mute)",
            border: "1px solid var(--p-hair)",
            background: "transparent",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "var(--p-ghost)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent";
          }}
        >
          Show all {totalQueries} queries
        </button>
      )}
    </div>
  );
}

function QueryBlock({
  query,
  engineResults,
  isLast,
}: {
  query: string;
  engineResults: TrackerResultClient[];
  isLast: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  // Build engine map for consistent ordering
  const byEngine = new Map<string, TrackerResultClient>();
  for (const r of engineResults) {
    byEngine.set(r.engine, r);
  }

  // Citation URL for this query (any engine)
  const citationUrl = engineResults.find((r) => r.citation_url)?.citation_url;

  return (
    <div
      style={{
        borderBottom: isLast ? "none" : "1px solid var(--p-hair)",
        paddingBottom: "20px",
        marginBottom: "20px",
      }}
    >
      {/* Query header */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div
          className="font-serif italic font-light text-[18px] leading-snug flex-1"
          style={{ color: "var(--paper-ink)" }}
        >
          {query}
        </div>
        <button
          onClick={() => setExpanded((v) => !v)}
          className="font-mono text-[8px] tracking-[0.14em] uppercase flex-shrink-0 mt-1 transition-opacity"
          style={{ color: "var(--p-faint)" }}
        >
          {expanded ? "Collapse" : "Excerpts"}
        </button>
      </div>

      {/* Per-engine rows */}
      <div className="flex flex-col gap-0">
        {ENGINES.map((engine) => {
          const result = byEngine.get(engine);
          if (!result) {
            return (
              <EngineRow
                key={engine}
                engine={engine}
                result={null}
                expanded={false}
              />
            );
          }
          return (
            <EngineRow
              key={engine}
              engine={engine}
              result={result}
              expanded={expanded}
            />
          );
        })}
      </div>

      {/* Citation URL chip */}
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
  expanded,
}: {
  engine: string;
  result: TrackerResultClient | null;
  expanded: boolean;
}) {
  const variant = result
    ? result.brand_cited
      ? "cited-paper"
      : result.brand_mentioned
        ? "mentioned-paper"
        : "not-found-paper"
    : "not-found-paper";

  const label = result
    ? result.brand_cited
      ? "Cited"
      : result.brand_mentioned
        ? "Mentioned"
        : "Not Found"
    : "No data";

  const excerpt = result?.response_text;
  const truncatedExcerpt = excerpt && excerpt.length > 280
    ? excerpt.slice(0, 280).trimEnd() + "..."
    : excerpt;

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

      {expanded && excerpt && (
        <div
          className="py-3 font-serif text-[13px] leading-relaxed"
          style={{
            color: "var(--p-mute)",
            borderBottom: "1px solid var(--p-ghost)",
            paddingLeft: "0",
          }}
        >
          {truncatedExcerpt}
        </div>
      )}
    </div>
  );
}
