import { ReportHeader } from "./ReportHeader";
import { KPIGrid } from "./KPIGrid";
import { CompetitorTable } from "./CompetitorTable";
import { QueryResultsTable } from "./QueryResultsTable";
import type {
  Report,
  TrackerRun,
  TrackerResultClient,
} from "@/lib/types";
import { weekRangeLabel } from "@/lib/utils";

interface ReportViewProps {
  report: Report;
  run: TrackerRun | null;
  results: TrackerResultClient[];
  clientName: string;
  brandName: string;
  domain?: string;
  previousRuns?: TrackerRun[];
}

export function ReportView({
  report,
  run,
  results,
  clientName,
  brandName,
  domain,
  previousRuns = [],
}: ReportViewProps) {
  const checkSvg = (
    <svg
      width="9"
      height="9"
      viewBox="0 0 9 9"
      fill="none"
      aria-hidden="true"
    >
      <polyline
        points="1,4.5 3.5,7 8,1.5"
        stroke="var(--ink)"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );

  return (
    <div
      className="max-w-[860px] mx-auto py-[70px] px-[76px]"
      style={{
        background: "var(--ink-2)",
        color: "var(--white)",
        fontFamily: "var(--display)",
      }}
    >
      <ReportHeader
        clientName={clientName}
        weekStart={report.week_start}
        domain={domain}
      />

      {report.exec_summary && (
        <div className="mt-[50px]">
          <h2
            className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
            style={{ color: "var(--mute)" }}
          >
            Executive Summary
          </h2>
          <p
            className="font-display font-light text-[22px] leading-[1.5] italic"
            style={{ color: "rgba(245,244,241,0.82)" }}
          >
            {report.exec_summary}
          </p>
        </div>
      )}

      {run && <KPIGrid run={run} previousRuns={previousRuns} />}

      {run && <CompetitorTable run={run} brandName={brandName} />}

      {results.length > 0 && <QueryResultsTable results={results} />}

      {report.search_console && (
        <div className="mt-[50px]">
          <h2
            className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
            style={{ color: "var(--mute)" }}
          >
            Search Performance
          </h2>
          <div className="grid grid-cols-4 gap-px bg-[var(--hair)] border border-[var(--hair)]">
            {(
              [
                ["Impressions", report.search_console.impressions, 0, ""],
                ["Clicks", report.search_console.clicks, 0, ""],
                ["Avg. CTR", report.search_console.ctr, 2, "%"],
                ["Avg. Position", report.search_console.position, 1, ""],
              ] as const
            ).map(([label, data, dp, suffix]) => (
              <div
                key={label}
                className="p-5 flex flex-col"
                style={{ background: "var(--ink-2)" }}
              >
                <div
                  className="font-mono text-[11px] tracking-[0.12em] uppercase mb-3"
                  style={{ color: "var(--mute)" }}
                >
                  {label}
                </div>
                <div
                  className="font-display font-light text-[40px] leading-none"
                  style={{ color: "var(--white)" }}
                >
                  {data?.week != null
                    ? `${data.week.toLocaleString("en-US", { minimumFractionDigits: dp, maximumFractionDigits: dp })}${suffix}`
                    : "—"}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {report.highlights.filter((h) => h.text.trim()).length > 0 && (
        <div className="mt-[50px]">
          <h2
            className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
            style={{ color: "var(--mute)" }}
          >
            Highlights / Wins
          </h2>
          <ul className="list-none">
            {report.highlights
              .filter((h) => h.text.trim())
              .map((h, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3.5 py-3 border-b border-[var(--hair)] font-display text-base leading-snug"
                  style={{ color: "var(--white)" }}
                >
                  <span style={{ color: "var(--accent)" }}>&mdash;</span>
                  <span>{h.text}</span>
                </li>
              ))}
          </ul>
        </div>
      )}

      {report.work_completed.filter((w) => w.text.trim()).length > 0 && (
        <div className="mt-[50px]">
          <h2
            className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
            style={{ color: "var(--mute)" }}
          >
            Work Completed This Week
          </h2>
          <ul className="list-none">
            {report.work_completed
              .filter((w) => w.text.trim())
              .map((w, i) => (
                <li
                  key={i}
                  className={`flex items-start gap-3.5 py-3 border-b border-[var(--hair)] font-display text-base leading-snug ${w.done ? "opacity-60" : ""}`}
                  style={{ color: "var(--white)" }}
                >
                  <span
                    className="w-[15px] h-[15px] min-w-[15px] mt-0.5 flex items-center justify-center shrink-0"
                    style={{
                      border: w.done
                        ? "none"
                        : "1px solid rgba(245,244,241,0.42)",
                      background: w.done ? "var(--white)" : "transparent",
                    }}
                  >
                    {w.done && checkSvg}
                  </span>
                  <span>{w.text}</span>
                </li>
              ))}
          </ul>
        </div>
      )}

      {report.priorities.filter((p) => p.text.trim()).length > 0 && (
        <div className="mt-[50px]">
          <h2
            className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
            style={{ color: "var(--mute)" }}
          >
            Next Week Priorities
          </h2>
          <ul className="list-none">
            {report.priorities
              .filter((p) => p.text.trim())
              .map((p, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3.5 py-3 border-b border-[var(--hair)] font-display text-base leading-snug"
                  style={{ color: "var(--white)" }}
                >
                  <span
                    className="font-mono text-[9px] tracking-[0.1em] shrink-0 min-w-[20px] pt-1"
                    style={{ color: "var(--accent)" }}
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span>{p.text}</span>
                </li>
              ))}
          </ul>
        </div>
      )}

      {report.blockers.filter((b) => b.text.trim()).length > 0 && (
        <div className="mt-[50px]">
          <h2
            className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
            style={{ color: "var(--mute)" }}
          >
            Blockers / Risks
          </h2>
          <ul className="list-none">
            {report.blockers
              .filter((b) => b.text.trim())
              .map((b, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3.5 py-3 border-b border-[var(--hair)] font-display text-base leading-snug"
                  style={{ color: "var(--white)" }}
                >
                  <span style={{ color: "var(--neg)" }}>&mdash;</span>
                  <span>{b.text}</span>
                </li>
              ))}
          </ul>
        </div>
      )}

      {report.notes && (
        <div className="mt-[50px]">
          <h2
            className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
            style={{ color: "var(--mute)" }}
          >
            Notes &amp; Observations
          </h2>
          <p
            className="font-display italic font-light text-base leading-[1.7]"
            style={{ color: "var(--mute)" }}
          >
            {report.notes}
          </p>
        </div>
      )}

      <footer
        className="mt-16 pt-4 border-t border-[var(--hair)] flex justify-between gap-3 flex-wrap font-mono text-[9px] tracking-[0.14em] uppercase"
        style={{ color: "var(--faint)" }}
      >
        <span>
          Prepared by Victory Velocity &middot;{" "}
          {domain || "victoryvelocity.ca"}
        </span>
        <span>{weekRangeLabel(report.week_start)}</span>
      </footer>
    </div>
  );
}
