import Link from "next/link";
import { formatRate, weekRangeLabel, scoreColor } from "@/lib/utils";
import type { Report, TrackerRun } from "@/lib/types";

interface ReportListProps {
  reports: (Report & { tracker_run: TrackerRun | null })[];
}

export function ReportList({ reports }: ReportListProps) {
  if (reports.length === 0) {
    return (
      <div
        className="font-mono text-[10px] tracking-[0.08em] uppercase py-6"
        style={{ color: "var(--faint)" }}
      >
        No reports published yet.
      </div>
    );
  }

  return (
    <div>
      <div
        className="font-mono text-xs tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-0"
        style={{ color: "var(--mute)" }}
      >
        Weekly Reports
      </div>

      {reports.map((report) => {
        const rate = report.tracker_run?.aggregate_mention_rate;
        return (
          <Link
            key={report.id}
            href={`/dashboard/reports/${report.id}`}
            className="flex items-center gap-3.5 py-[13px] border-b border-[var(--hair)] transition-all duration-300 hover:pl-3.5"
            style={{ color: "var(--white)" }}
          >
            <span className="font-serif italic text-lg flex-1">
              {weekRangeLabel(report.week_start)}
            </span>

            {rate != null && (
              <span
                className="font-mono text-[10px] tracking-[0.1em] font-bold"
                style={{ color: scoreColor(rate) }}
              >
                {formatRate(rate)}
              </span>
            )}

            <span
              className="font-mono text-[10px] tracking-[0.16em] uppercase w-24 text-right"
              style={{ color: "var(--faint)" }}
            >
              {report.published_at
                ? new Date(report.published_at).toLocaleDateString(
                    "en-US",
                    { month: "short", day: "numeric" }
                  )
                : ""}
            </span>

            <span
              className="font-sans text-[12.5px] font-medium tracking-[0.08em] transition-colors"
              style={{ color: "var(--faint)" }}
            >
              View →
            </span>
          </Link>
        );
      })}
    </div>
  );
}
