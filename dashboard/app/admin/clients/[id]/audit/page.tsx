export const dynamic = "force-dynamic";

import { createAdminClient } from "@/lib/supabase/admin";
import Link from "next/link";

export default async function AuditPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = createAdminClient();

  const { data: runs } = await supabase
    .from("audit_runs")
    .select("id, ran_at, site_score, pages_audited, weakest_pillar")
    .eq("client_id", id)
    .order("ran_at", { ascending: false });

  const allRuns = runs || [];

  return (
    <div>
      {allRuns.length === 0 ? (
        <p className="font-serif italic" style={{ color: "var(--mute)" }}>
          No audit runs yet. Run <code className="font-mono text-[10px]">python audit.py --client-id {id} --upload</code> to start the first one.
        </p>
      ) : (
        <>
          <div
            className="grid pb-2.5 border-b font-mono text-[8px] tracking-[0.14em] uppercase"
            style={{
              gridTemplateColumns: "1.5fr 80px 80px 1fr",
              gap: "16px",
              borderColor: "var(--hair)",
              color: "var(--faint)",
            }}
          >
            <span>DATE</span>
            <span>SCORE</span>
            <span>PAGES</span>
            <span>WEAKEST PILLAR</span>
          </div>

          {allRuns.map((run) => (
            <Link
              key={run.id}
              href={`/admin/clients/${id}/audit/${run.id}`}
              className="grid py-4 border-b transition-colors hover:bg-[var(--surface)]"
              style={{
                gridTemplateColumns: "1.5fr 80px 80px 1fr",
                gap: "16px",
                borderColor: "var(--hair)",
                textDecoration: "none",
              }}
            >
              <span className="font-mono text-[10px] tracking-[0.06em]" style={{ color: "var(--mute)" }}>
                {new Date(run.ran_at).toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" })}
              </span>
              <span className="font-serif text-[17px]" style={{ color: "var(--white)" }}>
                {run.site_score}<span className="font-mono text-[9px] ml-0.5" style={{ color: "var(--faint)" }}>/100</span>
              </span>
              <span className="font-mono text-[10px]" style={{ color: "var(--mute)" }}>
                {run.pages_audited}
              </span>
              <span className="font-mono text-[10px] tracking-[0.06em] uppercase" style={{ color: "var(--faint)" }}>
                {run.weakest_pillar}
              </span>
            </Link>
          ))}
        </>
      )}
    </div>
  );
}
