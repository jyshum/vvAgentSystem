import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { VisibilityOverview } from "@/components/dashboard/VisibilityOverview";
import { TrendChart } from "@/components/dashboard/TrendChart";
import { ReportList } from "@/components/dashboard/ReportList";
import type { TrackerRun, Report } from "@/lib/types";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  const { data: clientUser } = await supabase
    .from("client_users")
    .select("client_id")
    .eq("user_id", user.id)
    .single();

  if (!clientUser?.client_id) redirect("/login");

  const clientId = clientUser.client_id;

  const { data: client } = await supabase
    .from("clients")
    .select("*")
    .eq("id", clientId)
    .single();

  const { data: runs } = await supabase
    .from("tracker_runs")
    .select("*")
    .eq("client_id", clientId)
    .order("ran_at", { ascending: false });

  const { data: reports } = await supabase
    .from("reports")
    .select("*, tracker_run:tracker_runs(*)")
    .eq("client_id", clientId)
    .eq("status", "published")
    .order("week_start", { ascending: false });

  const allRuns = (runs as TrackerRun[]) || [];
  const latestRun = allRuns[0] || null;
  const previousRun = allRuns[1] || null;
  const allReports = (reports as (Report & { tracker_run: TrackerRun | null })[]) || [];

  return (
    <>
      <h1
        className="font-serif text-[clamp(34px,4.4vw,58px)] font-normal leading-[1.02] tracking-[-0.02em] mb-10"
        style={{ color: "var(--white)" }}
      >
        {client?.brand_name || client?.name || "Dashboard"}
      </h1>

      <VisibilityOverview
        latestRun={latestRun}
        previousRun={previousRun}
        totalReports={allReports.length}
      />

      <TrendChart runs={allRuns} />

      <ReportList reports={allReports} />
    </>
  );
}
