"use client";

import { useRouter } from "next/navigation";
import { productVisibilityScore } from "@/lib/intent-labels";
import { scoreColor, formatRate, formatDelta } from "@/lib/utils";
import type { Client, TrackerRun, Report } from "@/lib/types";

interface ClientRowProps {
  client: Client;
  latestRun: TrackerRun | null;
  previousRun: TrackerRun | null;
  latestReport: Report | null;
}

function checkStale(ranAt: string): boolean {
  return (Date.now() - new Date(ranAt).getTime()) > 7 * 24 * 60 * 60 * 1000;
}

export function ClientRow({ client, latestRun, previousRun }: ClientRowProps) {
  const router = useRouter();
  const latestRate = latestRun ? productVisibilityScore(latestRun)?.mention_rate ?? null : null;
  const previousRate = previousRun ? productVisibilityScore(previousRun)?.mention_rate ?? null : null;
  const mentionDelta = latestRate != null && previousRun
    ? formatDelta(latestRate, previousRate)
    : null;

  const isStale = latestRun ? checkStale(latestRun.ran_at) : true;

  return (
    <div
      onClick={() => router.push(`/admin/clients/${client.id}/runs`)}
      className="grid items-center py-5 px-4 border-b transition-all duration-[200ms] group cursor-pointer"
      style={{
        gridTemplateColumns: "2fr 1fr 1fr 1.4fr 80px",
        gap: "16px",
        borderColor: "var(--hair)",
      }}
      onMouseEnter={e => { e.currentTarget.style.background = "rgba(245,244,241,0.03)"; }}
      onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}
    >
      {/* Brand name + client name */}
      <div className="group-hover:pl-3 transition-all duration-[200ms]" style={{ transitionTimingFunction: "cubic-bezier(.2,.8,.2,1)" }}>
        <div className="font-serif text-[18px]" style={{ color: "var(--white)" }}>
          {client.brand_name || client.name}
        </div>
        <div className="font-mono text-[9px] tracking-[0.08em] mt-0.5" style={{ color: "var(--faint)" }}>
          {client.name}
        </div>
      </div>

      {/* Mention rate */}
      <div>
        {latestRun ? (
          <>
            <div className="font-display text-[26px] font-light leading-none"
              style={{ color: scoreColor(latestRate ?? 0) }}>
              {latestRate == null ? "—" : formatRate(latestRate)}
            </div>
            {mentionDelta && (
              <div className="font-mono text-[8px] mt-1" style={{
                color: mentionDelta.direction === "up" ? "var(--pos)"
                  : mentionDelta.direction === "down" ? "var(--neg)"
                  : "var(--faint)"
              }}>
                {mentionDelta.text}
              </div>
            )}
          </>
        ) : (
          <span className="font-mono text-[11px]" style={{ color: "var(--faint)" }}>—</span>
        )}
      </div>

      {/* Avg mention level */}
      <div>
        {latestRun ? (
          <div className="font-display text-[26px] font-light leading-none"
            style={{ color: (latestRun.aggregate_avg_mention_level ?? 0) >= 3 ? "var(--pos)" : (latestRun.aggregate_avg_mention_level ?? 0) >= 2 ? "var(--white)" : "var(--faint)" }}>
            {(latestRun.aggregate_avg_mention_level ?? 0).toFixed(1)}
          </div>
        ) : (
          <span className="font-mono text-[11px]" style={{ color: "var(--faint)" }}>—</span>
        )}
      </div>

      {/* Last run */}
      <div>
        {latestRun ? (
          <>
            <div className="font-mono text-[10px] tracking-[0.06em]" style={{ color: "var(--mute)" }}>
              {new Date(latestRun.ran_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
            </div>
            <div className="inline-flex items-center gap-1.5 mt-1.5 font-mono text-[8px] tracking-[0.1em] px-1.5 py-0.5 rounded-sm"
              style={isStale
                ? { background: "rgba(232,154,160,0.08)", color: "var(--neg)", border: "1px solid rgba(232,154,160,0.18)" }
                : { background: "rgba(132,216,171,0.1)", color: "var(--pos)", border: "1px solid rgba(132,216,171,0.2)" }
              }>
              <span className="w-1 h-1 rounded-full bg-current inline-block" />
              {isStale ? "STALE" : "CURRENT"}
            </div>
          </>
        ) : (
          <span className="font-mono text-[10px]" style={{ color: "var(--faint)" }}>No runs yet</span>
        )}
      </div>

      <div className="flex justify-end">
        <span
          className="font-mono text-[11px] transition-all duration-200 group-hover:translate-x-1 group-hover:opacity-100 opacity-40"
          style={{ color: "var(--faint)" }}
        >
          →
        </span>
      </div>
    </div>
  );
}
