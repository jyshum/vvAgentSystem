import { createClient } from "@/lib/supabase/server";
import Link from "next/link";
import { weekRangeLabel } from "@/lib/utils";
import type { Report } from "@/lib/types";

export default async function ReportsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

  const { data: reports } = await supabase
    .from("reports")
    .select("*")
    .eq("client_id", id)
    .order("created_at", { ascending: false });

  const allReports = (reports as Report[]) || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          {allReports.length} report{allReports.length !== 1 ? "s" : ""}
        </div>
        <Link
          href={`/api/admin/create-report?clientId=${id}`}
          className="font-mono text-[9px] tracking-[0.14em] uppercase py-3 px-5 transition-colors hover:text-white"
          style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}
        >
          + NEW BLANK REPORT
        </Link>
      </div>

      {allReports.length === 0 ? (
        <p className="font-serif italic" style={{ color: "var(--mute)" }}>
          No reports yet. Go to RUNS to create a report from a tracker run.
        </p>
      ) : (
        <>
          <div className="grid pb-3 border-b font-mono text-[8px] tracking-[0.18em] uppercase"
            style={{
              gridTemplateColumns: "1fr 120px auto",
              gap: "16px",
              borderColor: "var(--hair)",
              color: "var(--faint)",
            }}>
            <span>WEEK</span>
            <span>STATUS</span>
            <span></span>
          </div>

          {allReports.map((report) => (
            <div
              key={report.id}
              className="grid items-center py-4 border-b"
              style={{
                gridTemplateColumns: "1fr 120px auto",
                gap: "16px",
                borderColor: "var(--hair)",
              }}
            >
              <Link
                href={`/admin/clients/${id}/reports/${report.id}`}
                className="font-serif italic text-base hover:text-white transition-colors"
                style={{ color: "var(--mute)" }}
              >
                {weekRangeLabel(report.week_start) || "Untitled report"}
              </Link>
              <span
                className="font-mono text-[8px] tracking-[0.1em] uppercase py-1 px-2 inline-block text-center"
                style={
                  report.status === "published"
                    ? { color: "var(--pos)", border: "1px solid rgba(132,216,171,0.3)", background: "rgba(132,216,171,0.08)" }
                    : { color: "var(--faint)", border: "1px solid var(--hair)" }
                }
              >
                {report.status}
              </span>
              <div className="flex gap-2 justify-end">
                <Link
                  href={`/admin/clients/${id}/reports/${report.id}`}
                  className="font-mono text-[8px] tracking-[0.1em] uppercase py-1.5 px-3 transition-colors hover:text-white"
                  style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}
                >
                  EDIT
                </Link>
                <Link
                  href={`/admin/clients/${id}/reports/${report.id}/view`}
                  className="font-mono text-[8px] tracking-[0.1em] uppercase py-1.5 px-3 transition-colors hover:text-white"
                  style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}
                >
                  VIEW ↗
                </Link>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
