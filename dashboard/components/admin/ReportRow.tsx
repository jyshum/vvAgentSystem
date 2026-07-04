"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { weekRangeLabel, formatRate, scoreColor } from "@/lib/utils";
import type { Report, TrackerRun } from "@/lib/types";

interface ReportRowProps {
  report: Report;
  clientId: string;
  run: Pick<TrackerRun, "id" | "aggregate_mention_rate" | "aggregate_citation_rate"> | null;
}

export function ReportRow({ report, clientId, run }: ReportRowProps) {
  const router = useRouter();

  return (
    <div
      className="grid items-center py-[17px] border-b transition-all duration-200 group hover:pl-2.5 cursor-pointer"
      style={{
        gridTemplateColumns: "1.5fr 1fr 1fr 1fr 120px",
        gap: "16px",
        borderColor: "var(--hair)",
      }}
      onClick={() => router.push(`/admin/clients/${clientId}/reports/${report.id}`)}
    >
      {/* Week */}
      <div>
        <div className="font-serif text-[16px]" style={{ color: "var(--white)" }}>
          {weekRangeLabel(report.week_start) || "Untitled report"}
        </div>
        <div className="font-mono text-[8px] mt-0.5" style={{ color: "var(--faint)" }}>
          {report.status === "published" ? "● Published" : "Draft"}
        </div>
      </div>

      {/* Mention rate */}
      <div>
        {run ? (
          <div className="font-display font-light text-[22px] leading-none"
            style={{ color: scoreColor(run.aggregate_mention_rate) }}>
            {formatRate(run.aggregate_mention_rate)}
          </div>
        ) : (
          <span className="font-mono text-[11px]" style={{ color: "var(--faint)" }}>—</span>
        )}
      </div>

      {/* Citation rate */}
      <div>
        {run ? (
          <div className="font-display font-light text-[22px] leading-none"
            style={{ color: scoreColor(run.aggregate_citation_rate) }}>
            {formatRate(run.aggregate_citation_rate)}
          </div>
        ) : (
          <span className="font-mono text-[11px]" style={{ color: "var(--faint)" }}>—</span>
        )}
      </div>

      {/* Status */}
      <div className="font-mono text-[9px]" style={{ color: "var(--mute)" }}>
        {new Date(report.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
        {report.run_id ? " · from run" : " · blank"}
      </div>

      {/* Actions */}
      <div className="flex gap-1.5" onClick={(e) => e.stopPropagation()}>
        <Link
          href={`/admin/clients/${clientId}/reports/${report.id}`}
          className="font-mono text-[8px] tracking-[0.08em] py-1.5 px-2.5 transition-all duration-200 hover:text-white hover:border-[var(--ghost)]"
          style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}
        >
          EDIT
        </Link>
        <Link
          href={`/admin/clients/${clientId}/reports/${report.id}/view`}
          className="font-mono text-[8px] tracking-[0.08em] py-1.5 px-2.5 transition-all duration-200 hover:text-white hover:border-[var(--ghost)]"
          style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}
        >
          VIEW ↗
        </Link>
      </div>
    </div>
  );
}
