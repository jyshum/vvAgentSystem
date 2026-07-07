import { createAdminClient } from "@/lib/supabase/admin";
import { notFound } from "next/navigation";
import Link from "next/link";
import { SubTab } from "@/components/admin/SubTab";
import { TriggerRunButton } from "@/components/admin/TriggerRunButton";
import type { Client } from "@/lib/types";

export default async function ClientLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = createAdminClient();

  const { data: client } = await supabase
    .from("clients")
    .select("id, name, website_domain, cycle_frequency, cycle_day")
    .eq("id", id)
    .single();

  if (!client) notFound();
  const c = client as Pick<Client, "id" | "name" | "website_domain" | "cycle_frequency" | "cycle_day">;
  const tabs = [
    { label: "OVERVIEW", href: `/admin/clients/${id}/overview` },
    { label: "QUERIES", href: `/admin/clients/${id}/queries` },
    { label: "PAGES", href: `/admin/clients/${id}/pages` },
    { label: "RUNS", href: `/admin/clients/${id}/runs` },
    { label: "CARDS", href: `/admin/clients/${id}/cards` },
    { label: "CONFIG", href: `/admin/clients/${id}/config` },
    { label: "REPORTS", href: `/admin/clients/${id}/reports` },
  ];

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2.5 mb-0 pb-3.5 border-b font-mono text-[9px] tracking-[0.14em]" style={{ borderColor: "var(--hair)" }}>
        <Link
          href="/admin/clients"
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
          <div
            className="font-mono text-[8px] tracking-[0.06em] mt-1"
            style={{ color: "var(--faint)", opacity: 0.7 }}
          >
            {c.cycle_frequency === "monthly" ? "Monthly" : c.cycle_frequency === "biweekly" ? "Bi-weekly" : "Weekly"} · {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][c.cycle_day ?? 1]} 2:00 AM UTC
          </div>
        </div>
        <TriggerRunButton clientId={id} />
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
