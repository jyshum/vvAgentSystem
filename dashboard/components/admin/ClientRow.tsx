"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { scoreColor, formatRate, formatDelta } from "@/lib/utils";
import type { Client, TrackerRun, Report } from "@/lib/types";

interface ClientRowProps {
  client: Client;
  latestRun: TrackerRun | null;
  previousRun: TrackerRun | null;
  latestReport: Report | null; // kept for compatibility, unused
}

export function ClientRow({ client, latestRun, previousRun, latestReport }: ClientRowProps) {
  const router = useRouter();
  const mentionDelta = latestRun && previousRun
    ? formatDelta(latestRun.aggregate_mention_rate, previousRun.aggregate_mention_rate)
    : null;

  const isStale = latestRun
    ? (Date.now() - new Date(latestRun.ran_at).getTime()) > 7 * 24 * 60 * 60 * 1000
    : true;

  return (
    <div
      className="grid items-center py-5 px-4 border-b transition-all duration-[200ms] group cursor-pointer"
      style={{
        gridTemplateColumns: "2fr 1fr 1fr 1.4fr 80px",
        gap: "16px",
        borderColor: "var(--hair)",
      }}
      onClick={() => router.push(`/admin/clients/${client.id}/runs`)}
    >
      {/* Brand name + domain */}
      <div className="group-hover:pl-3 transition-all duration-[200ms]" style={{ transitionTimingFunction: "cubic-bezier(.2,.8,.2,1)" }}>
        <div className="font-serif text-[18px]" style={{ color: "var(--white)" }}>
          {client.brand_name || client.name}
        </div>
        <div className="font-mono text-[9px] tracking-[0.08em] mt-0.5" style={{ color: "var(--faint)" }}>
          {client.website_domain}
        </div>
      </div>

      {/* Mention rate */}
      <div>
        {latestRun ? (
          <>
            <div className="font-display text-[26px] font-light leading-none"
              style={{ color: scoreColor(latestRun.aggregate_mention_rate) }}>
              {formatRate(latestRun.aggregate_mention_rate)}
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

      {/* Citation rate */}
      <div>
        {latestRun ? (
          <div className="font-display text-[26px] font-light leading-none"
            style={{ color: scoreColor(latestRun.aggregate_citation_rate) }}>
            {formatRate(latestRun.aggregate_citation_rate)}
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

      {/* Open button */}
      <div onClick={(e) => e.stopPropagation()}>
        <button
          onClick={() => router.push(`/admin/clients/${client.id}/runs`)}
          className="font-mono text-[9px] tracking-[0.1em] py-1.5 px-3 transition-all duration-200 opacity-0 group-hover:opacity-100"
          style={{ color: "var(--faint)", border: "1px solid var(--hair)", background: "transparent" }}
          onMouseEnter={e => { (e.target as HTMLButtonElement).style.color = "var(--white)"; (e.target as HTMLButtonElement).style.borderColor = "var(--ghost)"; }}
          onMouseLeave={e => { (e.target as HTMLButtonElement).style.color = "var(--faint)"; (e.target as HTMLButtonElement).style.borderColor = "var(--hair)"; }}
        >
          OPEN →
        </button>
      </div>
    </div>
  );
}
