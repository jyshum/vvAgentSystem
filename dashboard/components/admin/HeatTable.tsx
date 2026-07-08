"use client";

import { useState } from "react";
import Link from "next/link";
import { formatRate } from "@/lib/utils";
import { QueryExpansion } from "@/components/admin/QueryExpansion";

export interface HeatCell {
  runId: string;
  ranAt: string;
  rate: number | null;
}

export interface HeatRow {
  query: string;
  cells: HeatCell[];
  stability: string;
  citedPct: number | null;
  page: { url: string; similarity: number; weak: boolean } | null;
  topCompetitor: { name: string; rate: number } | null;
  waiting: number;
}

interface HeatTableProps {
  rows: HeatRow[];
  clientId: string;
}

function heatBg(rate: number | null): string {
  if (rate === null) return "transparent";
  if (rate === 0) return "rgba(232,154,160,0.14)";
  if (rate < 0.25) return "rgba(253,126,20,0.12)";
  if (rate < 0.5) return "rgba(255,193,7,0.10)";
  return "rgba(132,216,171,0.14)";
}

const STABILITY_COLOR: Record<string, string> = {
  locked_in: "var(--pos)",
  gaining: "var(--pos)",
  declining: "var(--neg)",
  volatile: "#d4a017",
  absent: "var(--faint)",
};

function pagePathname(url: string): string {
  try {
    return new URL(url).pathname;
  } catch {
    return url;
  }
}

export function HeatTable({ rows, clientId }: HeatTableProps) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const cycleCount = rows[0]?.cells.length ?? 0;
  const cycleLabels =
    rows[0]?.cells.map((c) =>
      new Date(c.ranAt).toLocaleDateString("en-US", { month: "numeric", day: "numeric" })
    ) ?? [];

  const gridTemplate = `2fr repeat(${cycleCount}, 44px) 0.8fr 0.6fr 1.2fr 1fr 0.8fr`;

  return (
    <div>
      <div
        className="grid px-4 pb-3 border-b"
        style={{ gridTemplateColumns: gridTemplate, gap: 12, borderColor: "var(--hair)" }}
      >
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          QUERY
        </div>
        {cycleLabels.map((label, i) => (
          <div
            key={i}
            className="font-mono text-[8px] tracking-[0.18em] uppercase text-center"
            style={{ color: "var(--faint)" }}
          >
            {label}
          </div>
        ))}
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          STABILITY
        </div>
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          CITED
        </div>
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          PAGE
        </div>
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          TOP COMPETITOR
        </div>
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          WAITING
        </div>
      </div>

      {rows.map((row) => {
        const isExpanded = expanded === row.query;
        return (
          <div key={row.query}>
            <div
              onClick={() => setExpanded(isExpanded ? null : row.query)}
              className="grid items-center px-4 py-3 border-b cursor-pointer transition-colors"
              style={{
                gridTemplateColumns: gridTemplate,
                gap: 12,
                borderColor: "var(--hair)",
                background: isExpanded ? "rgba(245,244,241,0.03)" : "transparent",
              }}
            >
              <div className="font-serif text-[14px]" style={{ color: "var(--white)" }}>
                {row.query}
              </div>

              {row.cells.map((cell, i) => (
                <div
                  key={i}
                  className="font-mono text-[10px] text-center py-1"
                  style={{
                    background: heatBg(cell.rate),
                    color: cell.rate === null ? "var(--faint)" : "var(--white)",
                  }}
                >
                  {cell.rate === null ? "—" : formatRate(cell.rate)}
                </div>
              ))}

              <div
                className="font-mono text-[9px] lowercase"
                style={{ color: STABILITY_COLOR[row.stability] ?? "var(--faint)" }}
              >
                {row.stability}
              </div>

              <div className="font-mono text-[10px]" style={{ color: "var(--mute)" }}>
                {row.citedPct === null ? "—" : formatRate(row.citedPct)}
              </div>

              <div className="font-mono text-[9px]" style={{ color: "var(--mute)" }}>
                {row.page ? (
                  <>
                    {pagePathname(row.page.url)} {row.page.similarity.toFixed(2)}
                    {row.page.weak && (
                      <span
                        className="font-mono text-[8px] tracking-[0.08em] ml-1.5 px-1"
                        style={{ color: "#d4a017", border: "1px solid #d4a017" }}
                      >
                        WEAK
                      </span>
                    )}
                  </>
                ) : (
                  "—"
                )}
              </div>

              <div className="font-serif text-[12px]" style={{ color: "var(--mute)" }}>
                {row.topCompetitor
                  ? `${row.topCompetitor.name} ${formatRate(row.topCompetitor.rate)}`
                  : "—"}
              </div>

              <div>
                {row.waiting > 0 ? (
                  <Link
                    href="/admin/approvals"
                    onClick={(e) => e.stopPropagation()}
                    className="font-mono text-[8px] tracking-[0.08em] px-1.5 py-0.5"
                    style={{ color: "#d4a017", border: "1px solid #d4a017" }}
                  >
                    {row.waiting} WAITING
                  </Link>
                ) : (
                  <span className="font-mono text-[9px]" style={{ color: "var(--faint)" }}>
                    —
                  </span>
                )}
              </div>
            </div>

            {isExpanded && <QueryExpansion clientId={clientId} query={row.query} />}
          </div>
        );
      })}
    </div>
  );
}
