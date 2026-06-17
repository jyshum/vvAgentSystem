import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { SectionLabel } from "@/components/ui/SectionLabel";
import { InviteClientForm } from "@/components/admin/InviteClientForm";
import { formatRate, scoreColor, weekRangeLabel } from "@/lib/utils";
import type { Client, TrackerRun, Report } from "@/lib/types";

export default async function AdminClientDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

  const { data: client } = await supabase
    .from("clients")
    .select("*")
    .eq("id", id)
    .single();

  if (!client) notFound();

  const typedClient = client as Client;

  const { data: runs } = await supabase
    .from("tracker_runs")
    .select("*")
    .eq("client_id", id)
    .order("ran_at", { ascending: false });

  const { data: reports } = await supabase
    .from("reports")
    .select("*")
    .eq("client_id", id)
    .order("created_at", { ascending: false });

  const { data: users } = await supabase
    .from("client_users")
    .select("id, user_id, role, created_at")
    .eq("client_id", id);

  const allRuns = (runs as TrackerRun[]) || [];
  const allReports = (reports as Report[]) || [];

  return (
    <>
      <Link
        href="/admin"
        className="font-mono text-[11px] tracking-[0.16em] uppercase inline-block mb-10 transition-colors hover:text-[var(--mute)]"
        style={{ color: "var(--faint)" }}
      >
        &larr; Clients
      </Link>

      <h1
        className="font-serif text-[clamp(36px,5.2vw,64px)] font-normal leading-[1.04] tracking-[-0.025em] mb-2"
        style={{ color: "var(--white)" }}
      >
        {typedClient.name}
      </h1>

      <div
        className="font-mono text-[11px] tracking-[0.1em] uppercase mb-10"
        style={{ color: "var(--faint)" }}
      >
        {typedClient.website_domain || "No domain set"}
      </div>

      <Card elevated className="p-6 mb-8">
        <SectionLabel>Client Configuration</SectionLabel>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div
              className="font-mono text-[10px] tracking-[0.1em] uppercase mb-1"
              style={{ color: "var(--faint)" }}
            >
              Brand
            </div>
            <div className="font-serif text-base" style={{ color: "var(--white)" }}>
              {typedClient.brand_name}
            </div>
          </div>
          <div>
            <div
              className="font-mono text-[10px] tracking-[0.1em] uppercase mb-1"
              style={{ color: "var(--faint)" }}
            >
              Variations
            </div>
            <div className="flex flex-wrap gap-1">
              {(typedClient.brand_variations || []).map((v: string) => (
                <span
                  key={v}
                  className="font-mono text-[9px] tracking-[0.08em] py-0.5 px-2"
                  style={{
                    color: "var(--mute)",
                    border: "1px solid var(--ghost)",
                  }}
                >
                  {v}
                </span>
              ))}
            </div>
          </div>
          <div>
            <div
              className="font-mono text-[10px] tracking-[0.1em] uppercase mb-1"
              style={{ color: "var(--faint)" }}
            >
              Queries ({(typedClient.target_queries || []).length})
            </div>
            <ul className="list-none">
              {(typedClient.target_queries || []).map((q: string) => (
                <li
                  key={q}
                  className="font-serif italic text-sm py-0.5"
                  style={{ color: "var(--mute)" }}
                >
                  {q}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div
              className="font-mono text-[10px] tracking-[0.1em] uppercase mb-1"
              style={{ color: "var(--faint)" }}
            >
              Competitors ({(typedClient.competitors || []).length})
            </div>
            <div className="flex flex-wrap gap-1">
              {(typedClient.competitors || []).map((c: string) => (
                <span
                  key={c}
                  className="font-mono text-[9px] tracking-[0.08em] py-0.5 px-2"
                  style={{
                    color: "var(--mute)",
                    border: "1px solid var(--ghost)",
                  }}
                >
                  {c}
                </span>
              ))}
            </div>
          </div>
        </div>
      </Card>

      <Card elevated className="p-6 mb-8">
        <SectionLabel>Linked Users</SectionLabel>
        {(users || []).length > 0 ? (
          <div className="mb-4">
            {(users || []).map((u) => (
              <div
                key={u.id}
                className="flex items-center gap-3 py-2 border-b border-[var(--hair)]"
              >
                <span
                  className="font-mono text-[10px] tracking-[0.08em]"
                  style={{ color: "var(--mute)" }}
                >
                  {u.user_id}
                </span>
                <Badge variant={u.role === "admin" ? "published" : "draft"}>
                  {u.role}
                </Badge>
              </div>
            ))}
          </div>
        ) : (
          <p
            className="font-mono text-[10px] tracking-[0.08em] uppercase mb-4"
            style={{ color: "var(--faint)" }}
          >
            No users linked yet.
          </p>
        )}
        <InviteClientForm clientId={id} />
      </Card>

      <Card elevated className="p-6 mb-8">
        <SectionLabel>Tracker Run History</SectionLabel>
        {allRuns.length === 0 ? (
          <p
            className="font-mono text-[10px] tracking-[0.08em] uppercase"
            style={{ color: "var(--faint)" }}
          >
            No tracker runs yet. Run the tracker with --upload.
          </p>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th
                  className="font-mono text-[10px] tracking-[0.12em] uppercase text-left pb-2.5 border-b border-[var(--hair)]"
                  style={{ color: "var(--mute)" }}
                >
                  Date
                </th>
                <th
                  className="font-mono text-[10px] tracking-[0.12em] uppercase text-left pb-2.5 border-b border-[var(--hair)]"
                  style={{ color: "var(--mute)" }}
                >
                  Mention
                </th>
                <th
                  className="font-mono text-[10px] tracking-[0.12em] uppercase text-left pb-2.5 border-b border-[var(--hair)]"
                  style={{ color: "var(--mute)" }}
                >
                  Citation
                </th>
                <th className="pb-2.5 border-b border-[var(--hair)]"></th>
              </tr>
            </thead>
            <tbody>
              {allRuns.map((run) => {
                const hasReport = allReports.some(
                  (r) => r.run_id === run.id
                );
                return (
                  <tr key={run.id}>
                    <td
                      className="font-mono text-[11px] tracking-[0.08em] py-3 border-b border-[var(--hair)]"
                      style={{ color: "var(--mute)" }}
                    >
                      {new Date(run.ran_at).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                        hour: "numeric",
                        minute: "2-digit",
                      })}
                    </td>
                    <td className="py-3 border-b border-[var(--hair)]">
                      <span
                        className="font-bold"
                        style={{
                          color: scoreColor(run.aggregate_mention_rate),
                        }}
                      >
                        {formatRate(run.aggregate_mention_rate)}
                      </span>
                    </td>
                    <td className="py-3 border-b border-[var(--hair)]">
                      <span
                        className="font-bold"
                        style={{
                          color: scoreColor(run.aggregate_citation_rate),
                        }}
                      >
                        {formatRate(run.aggregate_citation_rate)}
                      </span>
                    </td>
                    <td className="py-3 border-b border-[var(--hair)] text-right">
                      {hasReport ? (
                        <span
                          className="font-mono text-[9px] tracking-[0.1em] uppercase"
                          style={{ color: "var(--faint)" }}
                        >
                          Report exists
                        </span>
                      ) : (
                        <Link
                          href={`/api/admin/create-report?runId=${run.id}&clientId=${run.client_id}`}
                          className="font-mono text-[9px] tracking-[0.1em] uppercase py-1 px-2 transition-colors"
                          style={{
                            color: "var(--white)",
                            border: "1px solid var(--ghost)",
                          }}
                        >
                          Create Report
                        </Link>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>

      <Card elevated className="p-6">
        <SectionLabel>Reports</SectionLabel>
        {allReports.length === 0 ? (
          <p
            className="font-mono text-[10px] tracking-[0.08em] uppercase"
            style={{ color: "var(--faint)" }}
          >
            No reports yet.
          </p>
        ) : (
          <div>
            {allReports.map((report) => (
              <Link
                key={report.id}
                href={`/admin/reports/${report.id}`}
                className="flex items-center gap-3.5 py-3 border-b border-[var(--hair)] transition-all duration-300 hover:pl-3.5"
                style={{ color: "var(--white)" }}
              >
                <span className="font-serif italic text-base flex-1">
                  {weekRangeLabel(report.week_start)}
                </span>
                <Badge
                  variant={
                    report.status === "published" ? "published" : "draft"
                  }
                >
                  {report.status}
                </Badge>
              </Link>
            ))}
          </div>
        )}
      </Card>
    </>
  );
}
