"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { scoreColor, formatRate } from "@/lib/utils";
import type { TrackerRun } from "@/lib/types";

interface RunRowProps {
  run: TrackerRun;
  clientId: string;
  hasReport: boolean;
  expectedQueries: number;
  resultCount: number;
}

export function RunRow({ run, clientId, hasReport, expectedQueries, resultCount }: RunRowProps) {
  const router = useRouter();
  const hasData = run.aggregate_mention_rate != null;
  const queryCount = resultCount > 0 ? Math.min(Math.round(resultCount / 4), expectedQueries) : 0;

  return (
    <div
      className="grid items-center py-[17px] border-b group transition-all duration-200 cursor-pointer hover:pl-3"
      style={{
        gridTemplateColumns: "1.5fr 1fr 1fr 80px 1fr 110px",
        gap: "16px",
        borderColor: "var(--hair)",
      }}
      onClick={() => router.push(`/admin/clients/${clientId}/runs/${run.id}`)}
    >
      {/* Date */}
      <div>
        <div className="font-serif text-[15px]" style={{ color: "var(--white)" }}>
          {new Date(run.ran_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
        </div>
        <div className="font-mono text-[8px] tracking-[0.06em] mt-0.5" style={{ color: "var(--faint)" }}>
          {new Date(run.ran_at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}
        </div>
      </div>

      {/* Mention */}
      <div>
        <div className="font-display font-light text-[22px] leading-none"
          style={{ color: hasData ? scoreColor(run.aggregate_mention_rate) : "var(--faint)" }}>
          {hasData ? formatRate(run.aggregate_mention_rate) : "—"}
        </div>
      </div>

      {/* Citation */}
      <div>
        <div className="font-display font-light text-[22px] leading-none"
          style={{ color: hasData ? scoreColor(run.aggregate_citation_rate) : "var(--faint)" }}>
          {hasData ? formatRate(run.aggregate_citation_rate) : "—"}
        </div>
      </div>

      {/* Queries */}
      <div className="font-mono text-[10px]" style={{ color: hasData ? "var(--mute)" : "var(--neg)" }}>
        {resultCount > 0 ? `${queryCount} / ${expectedQueries}` : "—"}
      </div>

      {/* Status */}
      <div>
        {hasData ? (
          <span
            className="inline-flex items-center gap-1.5 font-mono text-[7px] tracking-[0.1em] px-2 py-0.5 rounded-sm"
            style={{ background: "rgba(132,216,171,0.1)", color: "var(--pos)", border: "1px solid rgba(132,216,171,0.2)" }}
          >
            <span className="w-1 h-1 rounded-full bg-current inline-block" />OK
          </span>
        ) : (
          <span
            className="inline-flex items-center gap-1.5 font-mono text-[7px] tracking-[0.1em] px-2 py-0.5 rounded-sm"
            style={{ background: "rgba(232,154,160,0.08)", color: "var(--neg)", border: "1px solid rgba(232,154,160,0.18)" }}
          >
            <span className="w-1 h-1 rounded-full bg-current inline-block" />ERROR
          </span>
        )}
      </div>

      {/* Report */}
      <div onClick={(e) => e.stopPropagation()}>
        {hasReport ? (
          <button
            className="font-mono text-[8px] tracking-[0.08em] py-1.5 px-3 cursor-default"
            style={{ color: "var(--pos)", border: "1px solid rgba(132,216,171,0.25)" }}
          >
            ✓ REPORTED
          </button>
        ) : hasData ? (
          <Link
            href={`/api/admin/create-report?runId=${run.id}&clientId=${clientId}`}
            className="font-mono text-[8px] tracking-[0.08em] py-1.5 px-3 transition-all duration-200 hover:text-white hover:border-[var(--ghost)]"
            style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}
          >
            → MAKE REPORT
          </Link>
        ) : (
          <span className="font-mono text-[8px]" style={{ color: "var(--faint)", opacity: 0.4 }}>—</span>
        )}
      </div>
    </div>
  );
}
