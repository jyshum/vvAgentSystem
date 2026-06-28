import { createAdminClient } from "@/lib/supabase/admin";
import { notFound } from "next/navigation";
import Link from "next/link";
import { SubTab } from "@/components/admin/SubTab";
import { TriggerRunButton } from "@/components/admin/TriggerRunButton";
import type { Client, TrackerRun } from "@/lib/types";

export default async function ClientLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = createAdminClient();

  const [{ data: client }, { data: latestRuns }] = await Promise.all([
    supabase
      .from("clients")
      .select("id, name, website_domain")
      .eq("id", id)
      .single(),
    supabase
      .from("tracker_runs")
      .select("ran_at")
      .eq("client_id", id)
      .order("ran_at", { ascending: false })
      .limit(1),
  ]);

  if (!client) notFound();
  const c = client as Pick<Client, "id" | "name" | "website_domain">;
  const latestRunAt = (latestRuns as Pick<TrackerRun, "ran_at">[] | null)?.[0]?.ran_at ?? null;

  const tabs = [
    { label: "CONFIG", href: `/admin/clients/${id}/config` },
    { label: "RUNS", href: `/admin/clients/${id}/runs` },
    { label: "AUDIT", href: `/admin/clients/${id}/audit` },
  ];

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2.5 mb-0 pb-3.5 border-b font-mono text-[9px] tracking-[0.14em]" style={{ borderColor: "var(--hair)" }}>
        <Link
          href="/admin"
          className="uppercase transition-colors hover:text-[var(--white)]"
          style={{ color: "var(--faint)" }}
        >
          CLIENTS
        </Link>
        <span style={{ color: "var(--faint)", opacity: 0.4 }}>/</span>
        <span className="uppercase" style={{ color: "var(--mute)" }}>{c.name}</span>
      </div>

      {/* Client header */}
      <div className="pt-8 mb-0 flex items-start justify-between">
        <div>
          <h1
            className="font-display text-[48px] font-light leading-[0.95]"
            style={{ color: "var(--white)" }}
          >
            {c.name}
          </h1>
          <div
            className="font-mono text-[10px] tracking-[0.1em] mt-1.5"
            style={{ color: "var(--faint)" }}
          >
            {c.website_domain}
          </div>
        </div>
        <TriggerRunButton clientId={id} latestRunAt={latestRunAt} />
      </div>

      {/* Sub-nav */}
      <div
        className="flex gap-0 mt-[22px] border-b mb-10"
        style={{ borderColor: "var(--hair)" }}
      >
        {tabs.map((tab) => (
          <SubTab key={tab.label} label={tab.label} href={tab.href} />
        ))}
      </div>

      {children}
    </div>
  );
}
