import { createClient } from "@/lib/supabase/server";
import { ClientRow } from "@/components/admin/ClientRow";
import type { Client, TrackerRun, Report } from "@/lib/types";

export default async function AdminPage() {
  const supabase = await createClient();

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

  return (
    <>
      <div className="flex items-end justify-between mb-10">
        <div>
          <h1 className="font-display text-[clamp(34px,4.4vw,58px)] font-light leading-[1.02] tracking-[-0.01em]"
            style={{ color: "var(--white)" }}>
            Clients
          </h1>
          <p className="font-serif italic text-base mt-1" style={{ color: "var(--mute)" }}>
            {allClients.length} active account{allClients.length !== 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {/* Table header */}
      <div className="grid px-4 pb-3 border-b" style={{
        gridTemplateColumns: "2fr 1fr 1fr 1.4fr 1fr",
        gap: "16px",
        borderColor: "var(--hair)"
      }}>
        {["CLIENT", "MENTION", "CITATION", "LAST RUN", "REPORT"].map((h) => (
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
