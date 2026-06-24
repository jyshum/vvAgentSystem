import { createAdminClient } from "@/lib/supabase/admin";
import { notFound } from "next/navigation";

const PILLAR_ORDER = [
  "Content Structure",
  "Fact Density",
  "Source Citations",
  "Authority Signals",
  "Schema Markup",
  "Freshness",
];

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
          {PILLAR_ORDER.map((name) => (
            <div
              key={name}
              className="p-3"
              style={{ border: "1px solid var(--hair)" }}
            >
              <div className="font-mono text-[8px] tracking-[0.1em] uppercase mb-2" style={{ color: "var(--faint)" }}>
                {name}
              </div>
              <ScoreBadge score={pillarAverages[name] ?? 0} />
            </div>
          ))}
        </div>
      </div>

      {/* Pages */}
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
          <div
            key={page.id}
            className="grid py-3 border-b"
            style={{ gridTemplateColumns: "1fr 80px", gap: "16px", borderColor: "var(--hair)" }}
          >
            <span className="font-mono text-[10px] truncate" style={{ color: "var(--mute)" }}>
              {page.url}
            </span>
            <ScoreBadge score={page.total_score} />
          </div>
        ))}
      </div>

      {/* Action cards */}
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
                <span className="font-mono text-[8px]" style={{ color: "var(--faint)" }}>
                  {card.cms_action}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
