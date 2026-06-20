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
        stroke="var(--paper-ink)"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );

  const sectionHead = (title: string) => (
    <h2
      className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] mb-6"
      style={{
        color: "var(--p-mute)",
        borderBottom: "1px solid var(--p-hair)",
      }}
    >
      {title}
    </h2>
  );

  return (
    <div
      style={{
        maxWidth: "760px",
        margin: "0 auto",
        padding: "72px 80px 80px",
        background: "var(--paper)",
        color: "var(--paper-ink)",
        fontFamily: "var(--display)",
        boxShadow: "0 16px 80px rgba(0,0,0,0.6)",
      }}
    >
      <ReportHeader
        clientName={clientName}
        weekStart={report.week_start}
        domain={domain}
      />

      {/* Executive Summary */}
      {report.exec_summary && (
        <div className="mt-[50px]">
          {sectionHead("Executive Summary")}
          <p
            className="font-display font-light text-[22px] leading-[1.5] italic"
            style={{ color: "rgba(23,21,15,0.82)" }}
          >
            {report.exec_summary}
          </p>
        </div>
      )}

      {/* AI Visibility + Per-Engine */}
      {run && <KPIGrid run={run} previousRuns={previousRuns} />}

      {/* Google Search Console — moved up, tighter spacing after KPIGrid */}
      {report.search_console && (
        <div className="mt-[32px]">
          {sectionHead("Search Performance (GSC)")}
          <div
            className="grid grid-cols-4 gap-px"
            style={{
              background: "var(--p-hair)",
              border: "1px solid var(--p-hair)",
            }}
          >
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
                style={{ background: "var(--paper)" }}
              >
                <div
                  className="font-mono text-[11px] tracking-[0.12em] uppercase mb-3"
                  style={{ color: "var(--p-mute)" }}
                >
                  {label}
                </div>
                <div
                  className="font-display font-light text-[36px] leading-none"
                  style={{ color: "var(--paper-ink)" }}
                >
                  {data?.week != null
                    ? `${data.week.toLocaleString("en-US", {
                        minimumFractionDigits: dp,
                        maximumFractionDigits: dp,
                      })}${suffix}`
                    : "-"}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Competitor Table */}
      {run && <CompetitorTable run={run} brandName={brandName} />}

      {/* Query Results (includes citation URLs inline) */}
      {results.length > 0 && <QueryResultsTable results={results} brandName={brandName} brandVariations={[]} />}

      {/* Highlights */}
      {report.highlights.filter((h) => h.text.trim()).length > 0 && (
        <div className="mt-[50px]">
          {sectionHead("Highlights / Wins")}
          <ul className="list-none">
            {report.highlights
              .filter((h) => h.text.trim())
              .map((h, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3.5 py-3 font-display text-base leading-snug"
                  style={{
                    color: "var(--paper-ink)",
                    borderBottom: "1px solid var(--p-hair)",
                  }}
                >
                  <span style={{ color: "var(--pos-paper)" }}>-</span>
                  <span>{h.text}</span>
                </li>
              ))}
          </ul>
        </div>
      )}

      {/* Work Completed */}
      {report.work_completed.filter((w) => w.text.trim()).length > 0 && (
        <div className="mt-[50px]">
          {sectionHead("Work Completed This Week")}
          <ul className="list-none">
            {report.work_completed
              .filter((w) => w.text.trim())
              .map((w, i) => (
                <li
                  key={i}
                  className={`flex items-start gap-3.5 py-3 font-display text-base leading-snug ${w.done ? "opacity-60" : ""}`}
                  style={{
                    color: "var(--paper-ink)",
                    borderBottom: "1px solid var(--p-hair)",
                  }}
                >
                  <span
                    className="w-[15px] h-[15px] min-w-[15px] mt-0.5 flex items-center justify-center shrink-0"
                    style={{
                      border: w.done
                        ? "none"
                        : "1px solid var(--p-ghost)",
                      background: w.done ? "var(--paper-ink)" : "transparent",
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

      {/* Priorities */}
      {report.priorities.filter((p) => p.text.trim()).length > 0 && (
        <div className="mt-[50px]">
          {sectionHead("Next Week Priorities")}
          <ul className="list-none">
            {report.priorities
              .filter((p) => p.text.trim())
              .map((p, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3.5 py-3 font-display text-base leading-snug"
                  style={{
                    color: "var(--paper-ink)",
                    borderBottom: "1px solid var(--p-hair)",
                  }}
                >
                  <span
                    className="font-mono text-[9px] tracking-[0.1em] shrink-0 min-w-[20px] pt-1"
                    style={{ color: "var(--p-faint)" }}
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span>{p.text}</span>
                </li>
              ))}
          </ul>
        </div>
      )}

      {/* Blockers */}
      {report.blockers.filter((b) => b.text.trim()).length > 0 && (
        <div className="mt-[50px]">
          {sectionHead("Blockers / Risks")}
          <ul className="list-none">
            {report.blockers
              .filter((b) => b.text.trim())
              .map((b, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3.5 py-3 font-display text-base leading-snug"
                  style={{
                    color: "var(--paper-ink)",
                    borderBottom: "1px solid var(--p-hair)",
                  }}
                >
                  <span style={{ color: "var(--neg-paper)" }}>-</span>
                  <span>{b.text}</span>
                </li>
              ))}
          </ul>
        </div>
      )}

      {/* Notes */}
      {report.notes && (
        <div className="mt-[50px]">
          {sectionHead("Notes & Observations")}
          <p
            className="font-display italic font-light text-base leading-[1.7]"
            style={{ color: "var(--p-mute)" }}
          >
            {report.notes}
          </p>
        </div>
      )}

      <footer
        className="mt-16 pt-4 flex justify-between gap-3 flex-wrap font-mono text-[9px] tracking-[0.14em] uppercase"
        style={{
          color: "var(--p-faint)",
          borderTop: "1px solid var(--p-hair)",
        }}
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
