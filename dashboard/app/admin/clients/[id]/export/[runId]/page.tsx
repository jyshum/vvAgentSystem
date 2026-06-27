export const dynamic = "force-dynamic";

import { createAdminClient } from "@/lib/supabase/admin";
import { notFound } from "next/navigation";
import Link from "next/link";

export default async function ExportPage({
  params,
}: {
  params: Promise<{ id: string; runId: string }>;
}) {
  const { id, runId } = await params;
  const supabase = createAdminClient();

  const [{ data: client }, { data: run }, { data: cards }] = await Promise.all([
    supabase.from("clients").select("brand_name, website_domain").eq("id", id).single(),
    supabase.from("audit_runs").select("ran_at, site_score").eq("id", runId).single(),
    supabase
      .from("action_cards")
      .select("*")
      .eq("run_id", runId)
      .in("status", ["approved", "implemented"])
      .order("page_url"),
  ]);

  if (!run || !client) notFound();

  const allCards = cards || [];
  const grouped: Record<string, typeof allCards> = {};
  for (const card of allCards) {
    const url = card.page_url;
    if (!grouped[url]) grouped[url] = [];
    grouped[url].push(card);
  }

  return (
    <div style={{ maxWidth: 800 }}>
      <Link
        href={`/admin/clients/${id}/audit/${runId}`}
        className="inline-block font-mono text-[10px] tracking-[0.1em] uppercase mb-6 transition-colors hover:text-[var(--white)]"
        style={{ color: "var(--faint)", textDecoration: "none" }}
      >
        &larr; Back to Audit
      </Link>

      <div className="mb-8">
        <h1 className="font-display text-[36px] font-light leading-tight mb-2" style={{ color: "var(--white)" }}>
          Implementation Guide
        </h1>
        <div className="font-mono text-[9px] tracking-[0.1em]" style={{ color: "var(--faint)" }}>
          {client.brand_name} · {new Date(run.ran_at).toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" })} · {allCards.length} change{allCards.length !== 1 ? "s" : ""}
        </div>
      </div>

      {allCards.length === 0 ? (
        <p className="font-serif italic" style={{ color: "var(--mute)" }}>
          No approved cards for this audit run. Go back and approve some action cards first.
        </p>
      ) : (
        Object.entries(grouped).map(([url, pageCards]) => (
          <div key={url} className="mb-10">
            <div className="mb-4 pb-2" style={{ borderBottom: "1px solid var(--hair)" }}>
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-[11px] transition-colors hover:text-[var(--white)]"
                style={{ color: "var(--mute)", textDecoration: "none" }}
              >
                {url} ↗
              </a>
            </div>

            <div className="space-y-6">
              {pageCards.map((card) => (
                <div key={card.id} className="pl-4" style={{ borderLeft: "2px solid var(--hair)" }}>
                  <div className="font-mono text-[8px] tracking-[0.14em] uppercase mb-2" style={{ color: "var(--faint)" }}>
                    {card.pillar} · Score: {card.score}/100
                  </div>

                  <p className="font-serif text-[13px] mb-3" style={{ color: "var(--white)" }}>
                    {card.issue}
                  </p>

                  {card.before_text && (
                    <div className="mb-3">
                      <div className="font-mono text-[8px] tracking-[0.1em] uppercase mb-1" style={{ color: "var(--neg)" }}>
                        Find this text:
                      </div>
                      <pre className="font-mono text-[11px] p-3 whitespace-pre-wrap leading-relaxed" style={{ background: "rgba(232,154,160,0.05)", color: "var(--mute)", border: "1px solid rgba(232,154,160,0.15)" }}>
                        {card.before_text}
                      </pre>
                    </div>
                  )}

                  {card.after_text && (
                    <div className="mb-3">
                      <div className="font-mono text-[8px] tracking-[0.1em] uppercase mb-1" style={{ color: "var(--pos)" }}>
                        Replace with:
                      </div>
                      <pre className="font-mono text-[11px] p-3 whitespace-pre-wrap leading-relaxed" style={{ background: "rgba(132,216,171,0.05)", color: "var(--mute)", border: "1px solid rgba(132,216,171,0.15)" }}>
                        {card.after_text}
                      </pre>
                    </div>
                  )}

                  {card.code_block && (
                    <div className="mb-3">
                      <div className="font-mono text-[8px] tracking-[0.1em] uppercase mb-1" style={{ color: "var(--blue, #60a5fa)" }}>
                        Add this code:
                      </div>
                      <pre className="font-mono text-[11px] p-3 whitespace-pre-wrap leading-relaxed" style={{ background: "rgba(96,165,250,0.05)", color: "var(--mute)", border: "1px solid rgba(96,165,250,0.15)" }}>
                        {card.code_block}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
