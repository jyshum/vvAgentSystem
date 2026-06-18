import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import Link from "next/link";
import { SubTab } from "@/components/admin/SubTab";
import type { Client } from "@/lib/types";

export default async function ClientLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

  const { data: client } = await supabase
    .from("clients")
    .select("id, name, website_domain")
    .eq("id", id)
    .single();

  if (!client) notFound();
  const c = client as Pick<Client, "id" | "name" | "website_domain">;

  const tabs = [
    { label: "CONFIG", href: `/admin/clients/${id}/config` },
    { label: "RUNS", href: `/admin/clients/${id}/runs` },
    { label: "REPORTS", href: `/admin/clients/${id}/reports` },
  ];

  return (
    <div>
      {/* Breadcrumb */}
      <Link
        href="/admin"
        className="font-mono text-[11px] tracking-[0.16em] uppercase inline-block mb-6 opacity-60 hover:opacity-100 transition-opacity"
        style={{ color: "var(--faint)" }}
      >
        &larr; Clients
      </Link>

      {/* Client header */}
      <div className="mb-6">
        <h1
          className="font-display text-[clamp(34px,4.8vw,60px)] font-light leading-[1.02] tracking-[-0.02em]"
          style={{ color: "var(--white)" }}
        >
          {c.name}
        </h1>
        <div
          className="font-mono text-[10px] tracking-[0.1em] uppercase mt-1"
          style={{ color: "var(--faint)" }}
        >
          {c.website_domain}
        </div>
      </div>

      {/* Sub-nav */}
      <div
        className="flex gap-0 mb-10 border-b"
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
