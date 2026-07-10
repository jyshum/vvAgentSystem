import { createAdminClient } from "@/lib/supabase/admin";
import { ClientRow } from "@/components/admin/ClientRow";
import { AddClientButton } from "@/components/admin/AddClientButton";
import { RunAllButton } from "@/components/admin/RunAllButton";
import { productVisibilityScore } from "@/lib/intent-labels";
import type { Client, TrackerRun, Report } from "@/lib/types";

export default async function AdminPage() {
  const supabase = createAdminClient();

  const { data: clients } = await supabase
    .from("clients")
    .select("*")
    .order("created_at", { ascending: true });

  const allClients = (clients as Client[]) || [];

  const clientsWithData = await Promise.all(
    allClients.map(async (client) => {
      const { data: runs } = await supabase
        .from("tracker_runs")
        .select("*")
        .eq("client_id", client.id)
        .order("ran_at", { ascending: false })
        .limit(2);

      const { data: reports } = await supabase
        .from("reports")
        .select("*")
        .eq("client_id", client.id)
        .order("created_at", { ascending: false })
        .limit(1);

      const allRuns = (runs as TrackerRun[]) || [];
      return {
        client,
        latestRun: allRuns[0] || null,
        previousRun: allRuns[1] || null,
        latestReport: ((reports as Report[]) || [])[0] || null,
      };
    })
  );

  // Compute stats strip values
  const runsWithProductVisibility = clientsWithData
    .map(({ latestRun }) => (latestRun ? productVisibilityScore(latestRun)?.mention_rate ?? null : null))
    .filter((rate): rate is number => rate !== null);
  const avgMention = runsWithProductVisibility.length > 0
    ? runsWithProductVisibility.reduce((sum, rate) => sum + rate, 0) / runsWithProductVisibility.length
    : 0;
  const avgLevel = allClients.length > 0
    ? clientsWithData.reduce((sum, { latestRun }) => sum + (latestRun?.aggregate_avg_mention_level ?? 0), 0) / allClients.length
    : 0;

  return (
    <>
      <div className="flex items-end justify-between mb-10">
        <div>
          <h1 className="font-display text-[52px] font-light leading-[0.96]" style={{ color: "var(--white)" }}>
            Clients
          </h1>
          <p className="font-serif italic text-base mt-2" style={{ color: "var(--mute)" }}>
            {allClients.length} active account{allClients.length !== 1 ? "s" : ""}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <RunAllButton />
          <AddClientButton />
        </div>
      </div>

      {/* Stats strip */}
      <div className="grid grid-cols-3 mb-10" style={{ gap: 1, background: "var(--hair)", border: "1px solid var(--hair)" }}>
        <div className="py-[18px] px-[22px]" style={{ background: "var(--ink)" }}>
          <div className="font-display font-light text-[38px] leading-none mb-1.5" style={{ color: "var(--white)" }}>
            {allClients.length}
          </div>
          <div className="font-mono text-[8px] tracking-[0.14em]" style={{ color: "var(--faint)" }}>ACTIVE CLIENTS</div>
        </div>
        <div className="py-[18px] px-[22px]" style={{ background: "var(--ink)" }}>
          <div className="font-display font-light text-[38px] leading-none mb-1.5" style={{ color: avgMention > 0.5 ? "var(--pos)" : avgMention > 0.2 ? "var(--white)" : "var(--neg)" }}>
            {allClients.length > 0 ? Math.round(avgMention * 100) + "%" : "—"}
          </div>
          <div className="font-mono text-[8px] tracking-[0.14em]" style={{ color: "var(--faint)" }}>AVG PRODUCT VISIBILITY</div>
        </div>
        <div className="py-[18px] px-[22px]" style={{ background: "var(--ink)" }}>
          <div className="font-display font-light text-[38px] leading-none mb-1.5" style={{ color: avgLevel >= 3 ? "var(--pos)" : avgLevel >= 2 ? "var(--white)" : "var(--faint)" }}>
            {allClients.length > 0 ? avgLevel.toFixed(1) : "—"}
          </div>
          <div className="font-mono text-[8px] tracking-[0.14em]" style={{ color: "var(--faint)" }}>AVG MENTION LEVEL</div>
        </div>
      </div>

      {/* Table header */}
      <div className="grid px-4 pb-3 border-b" style={{
        gridTemplateColumns: "2fr 1fr 1fr 1.4fr 80px",
        gap: "16px",
        borderColor: "var(--hair)"
      }}>
        {["CLIENT", "PRODUCT VISIBILITY", "AVG LEVEL", "LAST RUN", ""].map((h) => (
          <div key={h} className="font-mono text-[8px] tracking-[0.18em]" style={{ color: "var(--faint)" }}>
            {h}
          </div>
        ))}
      </div>

      {allClients.length === 0 ? (
        <p className="font-serif italic text-base py-10" style={{ color: "var(--mute)" }}>
          No clients yet.
        </p>
      ) : (
        clientsWithData.map(({ client, latestRun, previousRun, latestReport }) => (
          <ClientRow
            key={client.id}
            client={client}
            latestRun={latestRun}
            previousRun={previousRun}
            latestReport={latestReport}
          />
        ))
      )}
    </>
  );
}
