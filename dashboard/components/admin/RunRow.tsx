"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { scoreColor, formatRate } from "@/lib/utils";
import type { TrackerRun } from "@/lib/types";

interface RunRowProps {
  run: TrackerRun;
  clientId: string;
  reportId: string | null;
  expectedQueries: number;
  resultCount: number;
}

export function RunRow({ run, clientId, reportId, expectedQueries, resultCount }: RunRowProps) {
  const router = useRouter();
  const hasData = run.aggregate_mention_rate != null;
  const queryCount = resultCount > 0 ? Math.min(Math.round(resultCount / 4), expectedQueries) : 0;
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  async function handleDelete(e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirmDelete) {
      setConfirmDelete(true);
      setTimeout(() => setConfirmDelete(false), 3000);
      return;
    }
    setDeleting(true);
    await fetch(`/api/admin/runs/${run.id}`, { method: "DELETE" });
    router.refresh();
  }

  return (
    <div
      className="grid items-center py-[17px] border-b group transition-all duration-200"
      style={{
        gridTemplateColumns: "1.5fr 0.8fr 0.8fr 0.7fr 0.7fr 80px 150px",
        gap: "16px",
        borderColor: "var(--hair)",
      }}
    >
      {/* Date */}
      <div className="transition-all duration-[200ms] group-hover:pl-3" style={{ transitionTimingFunction: "cubic-bezier(.2,.8,.2,1)" }}>
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

      {/* GSC Clicks */}
      <div>
        <div className="font-display font-light text-[22px] leading-none"
          style={{ color: run.gsc_clicks > 0 ? "var(--white)" : "var(--faint)" }}>
          {run.gsc_clicks > 0 ? run.gsc_clicks : "—"}
        </div>
      </div>

      {/* GSC Position */}
      <div>
        <div className="font-display font-light text-[22px] leading-none"
          style={{ color: run.gsc_position > 0 && run.gsc_position <= 10 ? "var(--pos)" : run.gsc_position > 10 ? "var(--yellow, #facc15)" : "var(--faint)" }}>
          {run.gsc_position > 0 ? run.gsc_position.toFixed(1) : "—"}
        </div>
      </div>

      {/* Queries */}
      <div className="font-mono text-[10px]" style={{ color: hasData ? "var(--mute)" : "var(--neg)" }}>
        {resultCount > 0 ? `${queryCount} / ${expectedQueries}` : "—"}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* VIEW RUN */}
        <Link
          href={`/admin/clients/${clientId}/runs/${run.id}`}
          className="font-mono text-[8px] tracking-[0.08em] py-1.5 px-2.5 transition-all duration-150 active:scale-[0.97]"
          style={{ color: "var(--white)", border: "1px solid var(--ghost)" }}
          onMouseEnter={e => { (e.currentTarget as HTMLAnchorElement).style.background = "var(--white)"; (e.currentTarget as HTMLAnchorElement).style.color = "var(--ink)"; }}
          onMouseLeave={e => { (e.currentTarget as HTMLAnchorElement).style.background = "transparent"; (e.currentTarget as HTMLAnchorElement).style.color = "var(--white)"; }}
        >
          VIEW RUN
        </Link>

        {/* REPORT / VIEW REPORT */}
        {reportId ? (
          <Link
            href={`/admin/clients/${clientId}/reports/${reportId}`}
            className="font-mono text-[8px] tracking-[0.08em] py-1.5 px-2.5 transition-all duration-150 active:scale-[0.97]"
            style={{ color: "var(--pos)", border: "1px solid rgba(132,216,171,0.3)" }}
            onMouseEnter={e => { (e.currentTarget as HTMLAnchorElement).style.background = "rgba(132,216,171,0.1)"; }}
            onMouseLeave={e => { (e.currentTarget as HTMLAnchorElement).style.background = "transparent"; }}
          >
            VIEW REPORT
          </Link>
        ) : hasData ? (
          <Link
            href={`/api/admin/create-report?runId=${run.id}&clientId=${clientId}`}
            className="font-mono text-[8px] tracking-[0.08em] py-1.5 px-2.5 transition-all duration-150 active:scale-[0.97]"
            style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}
            onMouseEnter={e => { (e.currentTarget as HTMLAnchorElement).style.color = "var(--white)"; (e.currentTarget as HTMLAnchorElement).style.borderColor = "var(--ghost)"; }}
            onMouseLeave={e => { (e.currentTarget as HTMLAnchorElement).style.color = "var(--faint)"; (e.currentTarget as HTMLAnchorElement).style.borderColor = "var(--hair)"; }}
          >
            REPORT
          </Link>
        ) : (
          <span className="font-mono text-[8px]" style={{ color: "var(--faint)", opacity: 0.3 }}>—</span>
        )}

        {/* DELETE (appears on hover) */}
        <button
          onClick={handleDelete}
          disabled={deleting}
          title={confirmDelete ? "Click again to confirm" : "Delete run"}
          className="font-mono text-[8px] tracking-[0.06em] py-1.5 px-2 opacity-0 group-hover:opacity-100 transition-all duration-150 active:scale-[0.97] disabled:opacity-30"
          style={{
            color: confirmDelete ? "var(--neg)" : "var(--faint)",
            border: confirmDelete ? "1px solid rgba(232,154,160,0.4)" : "1px solid transparent",
          }}
          onMouseEnter={e => { if (!confirmDelete) (e.currentTarget as HTMLButtonElement).style.color = "var(--neg)"; }}
          onMouseLeave={e => { if (!confirmDelete) (e.currentTarget as HTMLButtonElement).style.color = "var(--faint)"; }}
        >
          {deleting ? "..." : confirmDelete ? "CONFIRM" : "✕"}
        </button>
      </div>
    </div>
  );
}
