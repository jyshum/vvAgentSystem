import { createClient } from "@/lib/supabase/server";
import { ClientCard } from "@/components/admin/ClientCard";
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
        .limit(1);

      const { data: reports } = await supabase
        .from("reports")
        .select("*")
        .eq("client_id", client.id)
        .order("created_at", { ascending: false })
        .limit(1);

      return {
        client,
        latestRun: (runs?.[0] as TrackerRun) || null,
        latestReport: (reports?.[0] as Report) || null,
      };
    })
  );

  return (
    <>
      <div className="flex items-center justify-between mb-10">
        <h1
          className="font-serif text-[clamp(34px,4.4vw,58px)] font-normal leading-[1.02] tracking-[-0.02em]"
          style={{ color: "var(--white)" }}
        >
          Clients
        </h1>
      </div>

      {clientsWithData.length === 0 ? (
        <p
          className="font-serif text-lg italic"
          style={{ color: "var(--mute)" }}
        >
          No clients yet. Create one in Supabase or use the tracker upload.
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {clientsWithData.map(({ client, latestRun, latestReport }) => (
            <ClientCard
              key={client.id}
              client={client}
              latestRun={latestRun}
              latestReport={latestReport}
            />
          ))}
        </div>
      )}
    </>
  );
}
