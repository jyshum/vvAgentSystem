export const dynamic = "force-dynamic";

import { createAdminClient } from "@/lib/supabase/admin";
import { loadAuditTabData, lifecycleCounts } from "@/lib/technical-audit-data";
import { AuditSummary } from "@/components/audit/AuditSummary";
import { LifecycleStrip } from "@/components/audit/LifecycleStrip";
import { ActionCard } from "@/components/audit/ActionCard";
import { FindingsSections } from "@/components/audit/FindingsSections";
import { RunAuditButton } from "@/components/audit/RunAuditButton";

const LABEL = "font-mono text-[8px] uppercase tracking-[0.12em]";

export default async function AuditPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ run?: string }>;
}) {
  const { id } = await params;
  const { run: runParam } = await searchParams;

  const supabase = createAdminClient();
  const { data: client } = await supabase
    .from("clients")
    .select("website_domain")
    .eq("id", id)
    .maybeSingle();

  const { run, runs, results, groups, cards } = await loadAuditTabData(id, runParam);

  if (!run) {
    return (
      <div>
        <div className="mb-4 flex items-end justify-between gap-4">
          <h1 className="font-display text-[30px] font-light" style={{ color: "var(--white)" }}>
            Technical audit
          </h1>
          <RunAuditButton clientId={id} />
        </div>
        <p className="font-serif italic" style={{ color: "var(--mute)" }}>
          No audit has run for this client yet.
        </p>
      </div>
    );
  }

  if (run.status !== "completed") {
    const failed = run.status === "error";
    return (
      <div>
        <div className="mb-4 flex items-end justify-between gap-4">
          <h1
            className="font-display text-[30px] font-light"
            style={{ color: failed ? "var(--neg)" : "var(--white)" }}
          >
            Technical audit {failed ? "failed" : "running"}
          </h1>
          <RunAuditButton clientId={id} />
        </div>
        <p className="font-serif text-[13px]" style={{ color: "var(--mute)" }}>
          {failed
            ? run.error_message || "The audit stopped before producing a checklist."
            : "Evidence is still being collected. Reload in a moment."}
        </p>
      </div>
    );
  }

  const previousRunAt = runs.find(
    (item) => item.id !== run.id && new Date(item.started_at) < new Date(run.started_at),
  )?.started_at ?? null;

  const groupByKey = new Map(groups.map((group) => [group.group_key, group]));
  const resultsByKey = new Map<string, typeof results>();
  for (const group of groups) {
    resultsByKey.set(
      group.group_key,
      results.filter(
        (item) => item.check_id === group.check_id && group.subjects.includes(item.subject),
      ),
    );
  }

  const openCards = cards.filter(
    (card) => !["rejected", "verified"].includes(card.status),
  );

  return (
    <div>
      <AuditSummary run={run} clientId={id} domain={client?.website_domain ?? ""} />

      <LifecycleStrip counts={lifecycleCounts(results)} previousRunAt={previousRunAt} />

      {openCards.length > 0 && (
        <section className="mb-8">
          <div className={`mb-2.5 ${LABEL}`} style={{ color: "var(--faint)" }}>
            Needs action · {openCards.length} cards
          </div>
          {openCards.map((card) => (
            <ActionCard
              key={card.id}
              card={card}
              group={card.group_key ? groupByKey.get(card.group_key) : undefined}
              results={card.group_key ? resultsByKey.get(card.group_key) ?? [] : []}
            />
          ))}
        </section>
      )}

      <div className={`mb-2.5 ${LABEL}`} style={{ color: "var(--faint)" }}>
        All findings
      </div>
      <FindingsSections run={run} results={results} />
    </div>
  );
}
