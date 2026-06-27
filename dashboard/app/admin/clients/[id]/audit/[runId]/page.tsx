export const dynamic = "force-dynamic";

import { createAdminClient } from "@/lib/supabase/admin";
import { notFound } from "next/navigation";
import Link from "next/link";
import { PageScoreRow } from "./PageScoreRow";

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 60 ? "var(--green, #4ade80)" : score >= 40 ? "var(--yellow, #facc15)" : "var(--red, #f87171)";
  return (
    <span className="font-serif text-[17px]" style={{ color }}>
      {score}
      <span className="font-mono text-[9px] ml-0.5" style={{ color: "var(--faint)" }}>
        /100
      </span>
    </span>
  );
}

export default async function AuditRunPage({
  params,
}: {
  params: Promise<{ id: string; runId: string }>;
}) {
  const { id, runId } = await params;
  const supabase = createAdminClient();

  const [{ data: run }, { data: pages }, { data: cards }] = await Promise.all([
    supabase.from("audit_runs").select("*").eq("id", runId).single(),
    supabase.from("page_scores").select("*").eq("run_id", runId).order("total_score", { ascending: true }),
    supabase.from("action_cards").select("*").eq("run_id", runId).order("score", { ascending: true }),
  ]);

  if (!run) notFound();

  const pillarAverages: Record<string, number> = run.pillar_averages || {};
  const allPages = pages || [];
  const allCards = cards || [];

  return (
    <div className="space-y-10">
      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Link
          href={`/admin/clients/${id}/audit`}
          className="inline-block font-mono text-[10px] tracking-[0.1em] uppercase transition-colors hover:text-[var(--white)]"
          style={{ color: "var(--faint)", textDecoration: "none" }}
        >
          &larr; Back to Audit Runs
        </Link>
        {allCards.length > 0 && (
          <Link
            href={`/admin/clients/${id}/export/${runId}`}
            className="font-mono text-[10px] tracking-[0.14em] uppercase py-2.5 px-5 transition-all duration-200 hover:opacity-80"
            style={{ background: "var(--white)", color: "var(--ink)", textDecoration: "none" }}
          >
            EXPORT CHANGES
          </Link>
        )}
      </div>

      {/* Site score */}
      <div>
        <div className="font-mono text-[9px] tracking-[0.14em] uppercase mb-2" style={{ color: "var(--faint)" }}>
          Site Score — {new Date(run.ran_at).toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" })}
        </div>
        <div className="font-display text-[64px] font-light leading-none" style={{ color: "var(--white)" }}>
          {run.site_score}
          <span className="font-mono text-[20px]" style={{ color: "var(--faint)" }}>/100</span>
        </div>
      </div>

      {/* Pillar averages */}
      <div>
        <div className="font-mono text-[9px] tracking-[0.14em] uppercase mb-4" style={{ color: "var(--faint)" }}>
          Pillar Averages
        </div>
        <div className="grid grid-cols-3 gap-3">
          {Object.entries(pillarAverages).map(([name, score]) => (
            <div
              key={name}
              className="p-3"
              style={{ border: "1px solid var(--hair)" }}
            >
              <div className="font-mono text-[8px] tracking-[0.1em] uppercase mb-2" style={{ color: "var(--faint)" }}>
                {name}
              </div>
              <ScoreBadge score={score} />
            </div>
          ))}
        </div>
      </div>

      {/* Pages — expandable rows */}
      <div>
        <div className="font-mono text-[9px] tracking-[0.14em] uppercase mb-4" style={{ color: "var(--faint)" }}>
          Pages Audited ({allPages.length})
        </div>
        <div
          className="grid pb-2.5 border-b font-mono text-[8px] tracking-[0.14em] uppercase"
          style={{
            gridTemplateColumns: "1fr 80px",
            gap: "16px",
            borderColor: "var(--hair)",
            color: "var(--faint)",
          }}
        >
          <span>URL</span>
          <span>SCORE</span>
        </div>
        {allPages.map((page) => (
          <PageScoreRow
            key={page.id}
            page={page}
          />
        ))}
      </div>

      {/* Action cards summary */}
      {allCards.length > 0 && (
        <div>
          <div className="font-mono text-[9px] tracking-[0.14em] uppercase mb-4" style={{ color: "var(--faint)" }}>
            Action Cards ({allCards.length})
          </div>
          <div className="space-y-4">
            {allCards.map((card) => (
              <div key={card.id} style={{ border: "1px solid var(--hair)" }} className="p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="space-y-1">
                    <div className="font-mono text-[8px] tracking-[0.14em] uppercase" style={{ color: "var(--faint)" }}>
                      {card.pillar}
                    </div>
                    <div className="font-mono text-[9px]" style={{ color: "var(--mute)" }}>
                      {card.page_url}
                    </div>
                  </div>
                  <ScoreBadge score={card.score} />
                </div>

                <p className="font-serif text-[13px] mb-4" style={{ color: "var(--white)" }}>
                  {card.issue}
                </p>

                {card.before_text && (
                  <div className="mb-3">
                    <div className="font-mono text-[8px] tracking-[0.1em] uppercase mb-1.5" style={{ color: "var(--faint)" }}>Before</div>
                    <pre className="font-mono text-[10px] p-3 whitespace-pre-wrap" style={{ background: "var(--surface)", color: "var(--red, #f87171)" }}>
                      {card.before_text}
                    </pre>
                  </div>
                )}

                {card.after_text && (
                  <div className="mb-3">
                    <div className="font-mono text-[8px] tracking-[0.1em] uppercase mb-1.5" style={{ color: "var(--faint)" }}>After</div>
                    <pre className="font-mono text-[10px] p-3 whitespace-pre-wrap" style={{ background: "var(--surface)", color: "var(--green, #4ade80)" }}>
                      {card.after_text}
                    </pre>
                  </div>
                )}

                {card.code_block && (
                  <div className="mb-3">
                    <div className="font-mono text-[8px] tracking-[0.1em] uppercase mb-1.5" style={{ color: "var(--faint)" }}>Code to inject</div>
                    <pre className="font-mono text-[10px] p-3 whitespace-pre-wrap" style={{ background: "var(--surface)", color: "var(--blue, #60a5fa)" }}>
                      {card.code_block}
                    </pre>
                  </div>
                )}

                <div className="flex items-center gap-3 mt-3">
                  <span
                    className="font-mono text-[8px] tracking-[0.1em] uppercase px-2 py-0.5"
                    style={{
                      background: card.status === "implemented" ? "rgba(74,222,128,0.1)" : card.status === "approved" ? "rgba(96,165,250,0.1)" : "var(--surface)",
                      color: card.status === "implemented" ? "var(--green, #4ade80)" : card.status === "approved" ? "var(--blue, #60a5fa)" : "var(--faint)",
                    }}
                  >
                    {card.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {allCards.length === 0 && (
        <div>
          <div className="font-mono text-[9px] tracking-[0.14em] uppercase mb-4" style={{ color: "var(--faint)" }}>
            Action Cards
          </div>
          <p className="font-serif italic text-[13px]" style={{ color: "var(--mute)" }}>
            No action cards for this audit run. Re-run the audit to generate recommendations.
          </p>
        </div>
      )}
    </div>
  );
}
