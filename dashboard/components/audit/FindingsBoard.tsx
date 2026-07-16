import {
  TECHNICAL_AUDIT_STATUS_COLOR,
  TECHNICAL_AUDIT_STATUS_LABEL,
  type TechnicalAuditActionCard,
  type TechnicalAuditFindingGroup,
  type TechnicalAuditResult,
  type TechnicalAuditRun,
} from "@/lib/technical-audit-types";
import { ActionCard } from "@/components/audit/ActionCard";
import { findingTitle } from "@/lib/technical-audit-labels";

const ATTENTION = ["fail", "review", "unknown"];
const CARD_CLOSED = ["rejected", "verified"];

function sectionLabel(section: string): string {
  return section.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

/** One remediation card, expanded from its finding row. The red rail + tint is
 *  the same accent as the pulsing summary, so the eye tracks from the row it
 *  clicked into the card it opened. */
type Priority = {
  card: TechnicalAuditActionCard;
  group: TechnicalAuditFindingGroup | undefined;
  results: TechnicalAuditResult[];
};

function PriorityRow({ priority }: { priority: Priority }) {
  const { card, group, results } = priority;
  const status = group?.status ?? "fail";
  const color = TECHNICAL_AUDIT_STATUS_COLOR[status];
  const subjectCount = group?.subjects.length ?? results.length;
  const heading = findingTitle(group?.check_id, group?.summary ?? card.title);

  return (
    <details className="vv-priority border-t first:border-t-0" style={{ borderColor: "var(--hair)" }}>
      <summary className="cursor-pointer list-none px-4 py-3 [&::-webkit-details-marker]:hidden">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="font-serif text-[15px]" style={{ color: "var(--white)" }}>
              {heading}
            </div>
            <div className="mt-1 font-mono text-[9px]" style={{ color: "var(--faint)" }}>
              {subjectCount} {subjectCount === 1 ? "page" : "pages"} · needs action
            </div>
          </div>
          <span
            className="shrink-0 border px-2 py-1 font-mono text-[8px] uppercase tracking-[0.12em]"
            style={{ color, borderColor: color }}
          >
            {TECHNICAL_AUDIT_STATUS_LABEL[status]}
          </span>
        </div>
      </summary>
      <div
        className="px-3 pb-1 pt-3"
        style={{ borderLeft: "2px solid var(--neg)", background: "rgba(232, 154, 160, 0.05)" }}
      >
        <ActionCard card={card} group={group} results={results} />
      </div>
    </details>
  );
}

function EvidenceField({ label, value }: { label: string; value: string }) {
  return (
    <div className="px-4 py-3" style={{ background: "var(--ink-soft)" }}>
      <div className="mb-1 font-mono text-[8px] uppercase tracking-[0.12em]" style={{ color: "var(--faint)" }}>
        {label}
      </div>
      <div className="font-serif text-[13px] leading-relaxed" style={{ color: "var(--mute)" }}>
        {value}
      </div>
    </div>
  );
}

function EvidenceRow({ result }: { result: TechnicalAuditResult }) {
  const needsAttention = ATTENTION.includes(result.status);
  const color = TECHNICAL_AUDIT_STATUS_COLOR[result.status];
  // Surface the "why" on the collapsed row for skipped checks, so a reader sees
  // why something was not applicable without opening every box.
  const closedReason = result.status === "not_applicable" ? result.applicability.reason : null;

  return (
    <details open={needsAttention} className="border-t first:border-t-0" style={{ borderColor: "var(--hair)" }}>
      <summary className="cursor-pointer list-none px-4 py-3 [&::-webkit-details-marker]:hidden">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="font-serif text-[15px]" style={{ color: "var(--white)" }}>
              {findingTitle(result.check_id, result.summary)}
            </div>
            <div className="mt-1 break-all font-mono text-[9px]" style={{ color: "var(--faint)" }}>
              {result.subject}
            </div>
            {closedReason && (
              <div className="mt-1 font-serif text-[12px] italic" style={{ color: "var(--faint)" }}>
                {closedReason}
              </div>
            )}
          </div>
          <span
            className="shrink-0 border px-2 py-1 font-mono text-[8px] uppercase tracking-[0.12em]"
            style={{ color, borderColor: color }}
          >
            {TECHNICAL_AUDIT_STATUS_LABEL[result.status]}
          </span>
        </div>
      </summary>

      <div className="grid gap-px border-t md:grid-cols-2" style={{ background: "var(--hair)", borderColor: "var(--hair)" }}>
        <EvidenceField label="Expected" value={result.expected} />
        <EvidenceField label="Why this applies" value={result.applicability.reason} />
        <EvidenceField
          label="Next action"
          value={`${result.next_action.instruction} · owner: ${result.next_action.owner}`}
        />
        <EvidenceField label="Scope" value={`${JSON.stringify(result.scope)} · confidence: ${result.confidence}`} />
        <div className="md:col-span-2 px-4 py-3" style={{ background: "var(--ink-soft)" }}>
          <div className="mb-1.5 font-mono text-[8px] uppercase tracking-[0.12em]" style={{ color: "var(--faint)" }}>
            Observed evidence
          </div>
          <pre
            className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-[10px] leading-relaxed"
            style={{ color: "var(--mute)" }}
          >
            {JSON.stringify(result.observed, null, 2)}
          </pre>
        </div>
      </div>
    </details>
  );
}

type SectionBucket = { priorities: Priority[]; evidence: TechnicalAuditResult[] };

export function FindingsBoard({
  run,
  results,
  groups,
  cards,
}: {
  run: TechnicalAuditRun;
  results: TechnicalAuditResult[];
  groups: TechnicalAuditFindingGroup[];
  cards: TechnicalAuditActionCard[];
}) {
  if (run.status !== "completed") {
    const failed = run.status === "error";
    return (
      <section className="mb-8 border px-5 py-5" style={{ borderColor: failed ? "var(--neg)" : "var(--hair)" }}>
        <h2 className="font-display text-[28px] font-light" style={{ color: failed ? "var(--neg)" : "var(--white)" }}>
          Technical audit {failed ? "failed" : "running"}
        </h2>
        <p className="mt-2 font-serif text-[13px]" style={{ color: "var(--mute)" }}>
          {failed
            ? run.error_message || "The audit stopped before producing a valid checklist."
            : "Evidence is still being collected. Findings will appear after completion."}
        </p>
      </section>
    );
  }

  const groupByKey = new Map(groups.map((group) => [group.group_key, group]));
  const resultsForGroup = (group: TechnicalAuditFindingGroup) =>
    results.filter(
      (item) => item.check_id === group.check_id && group.subjects.includes(item.subject),
    );

  // An open action card becomes a priority row, attached to the section of the
  // finding it remediates. Its results are "carried" so they are not also
  // repeated as raw evidence rows below.
  const openCards = cards.filter((card) => !CARD_CLOSED.includes(card.status));
  const carried = new Set<string>();
  const priorities: (Priority & { section: string })[] = [];
  const orphanCards: Priority[] = [];

  for (const card of openCards) {
    const group = card.group_key ? groupByKey.get(card.group_key) : undefined;
    const groupResults = group ? resultsForGroup(group) : [];
    groupResults.forEach((item) => carried.add(item.id));
    const section = groupResults[0]?.section;
    const priority: Priority = { card, group, results: groupResults };
    if (section) priorities.push({ ...priority, section });
    else orphanCards.push(priority); // community / group-less card, no finding row to host it
  }

  // Preserve first-seen section order from the results stream, same as the
  // original checklist grouping.
  const sections = new Map<string, SectionBucket>();
  for (const result of results) {
    if (!sections.has(result.section)) sections.set(result.section, { priorities: [], evidence: [] });
    if (!carried.has(result.id)) sections.get(result.section)!.evidence.push(result);
  }
  for (const priority of priorities) {
    if (!sections.has(priority.section)) sections.set(priority.section, { priorities: [], evidence: [] });
    sections.get(priority.section)!.priorities.push(priority);
  }

  return (
    <section className="mb-8">
      {orphanCards.length > 0 && (
        <div className="mb-4 border" style={{ borderColor: "rgba(232, 154, 160, 0.4)" }}>
          <div className="px-4 py-3 font-mono text-[9px] uppercase tracking-[0.12em]" style={{ color: "var(--faint)", background: "var(--ink-2)" }}>
            Opportunities · {orphanCards.length}
          </div>
          <div style={{ background: "var(--ink)" }}>
            {orphanCards.map((priority) => (
              <PriorityRow key={priority.card.id} priority={priority} />
            ))}
          </div>
        </div>
      )}

      <div className="border" style={{ borderColor: "var(--hair)" }}>
        {[...sections.entries()].map(([section, bucket]) => {
          const rowCount = bucket.priorities.length + bucket.evidence.length;
          const attention =
            bucket.priorities.length > 0 || bucket.evidence.some((item) => ATTENTION.includes(item.status));
          return (
            <details key={section} open={attention} className="border-b last:border-b-0" style={{ borderColor: "var(--hair)" }}>
              <summary
                className="flex cursor-pointer items-center justify-between gap-3 px-4 py-3 font-mono text-[9px] uppercase tracking-[0.12em]"
                style={{ color: "var(--mute)", background: "var(--ink-2)" }}
              >
                <span>
                  {sectionLabel(section)} · {rowCount}
                </span>
                {bucket.priorities.length > 0 && (
                  <span style={{ color: "var(--neg)" }}>{bucket.priorities.length} to act</span>
                )}
              </summary>
              <div style={{ background: "var(--ink)" }}>
                {bucket.priorities.map((priority) => (
                  <PriorityRow key={priority.card.id} priority={priority} />
                ))}
                {bucket.evidence.map((result) => (
                  <EvidenceRow key={result.id} result={result} />
                ))}
              </div>
            </details>
          );
        })}
      </div>
    </section>
  );
}
