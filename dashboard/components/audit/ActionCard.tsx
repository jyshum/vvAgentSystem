import {
  CARD_STATUS_LABEL,
  LIFECYCLE_COLOR,
  LIFECYCLE_LABEL,
  TECHNICAL_AUDIT_STATUS_COLOR,
  TECHNICAL_AUDIT_STATUS_LABEL,
  type TechnicalAuditActionCard,
  type TechnicalAuditFindingGroup,
  type TechnicalAuditLifecycleState,
  type TechnicalAuditResult,
} from "@/lib/technical-audit-types";
import { CardActions } from "@/components/audit/CardActions";
import { findingTitle, GENERIC_UNKNOWN_SUMMARY } from "@/lib/technical-audit-labels";

const CHIP =
  "shrink-0 border px-2 py-1 font-mono text-[8px] uppercase tracking-[0.12em]";
const LABEL = "font-mono text-[8px] uppercase tracking-[0.12em]";

/** The card lists at most this many observed facts; the true total is always
 *  stated alongside them so a long tail is never hidden. */
const FACT_LIMIT = 10;

/** copy_values carries observed facts only (lists of failing URLs, dead
 *  sources, insecure resources). Never drafted prose - see the spec.
 *  Returns every fact found: truncation is a presentation concern, and the
 *  caller needs the true count to report it honestly.
 *
 *  The backend caps each fact list at 10 entries before persisting the card,
 *  and (for lists that can run long) records the true count alongside it as
 *  `<key>_total`. `total` here is the sum, across every fact array in
 *  copy_values, of its declared `<key>_total` when present or its raw
 *  array length otherwise (older cards persisted before totals existed have
 *  no `_total` key, so their array length - already capped at the time -
 *  is the only count available). This keeps the rule generic: a fifth
 *  remediation that adds a fact array gets correct totals for free as long
 *  as it follows the `<key>` / `<key>_total` convention. */
function observedFacts(copyValues: Record<string, unknown>): { facts: string[]; total: number } {
  const facts: string[] = [];
  let total = 0;
  for (const [key, value] of Object.entries(copyValues)) {
    if (!Array.isArray(value)) continue;
    for (const item of value) {
      if (typeof item === "string") facts.push(item);
      else if (item && typeof item === "object") {
        const record = item as Record<string, unknown>;
        const url = record.url ?? record.href ?? record.target;
        const detail = record.status ?? record.reason;
        if (typeof url === "string") {
          facts.push(detail === undefined ? url : `${url} - ${String(detail)}`);
        }
      }
    }
    const declaredTotal = copyValues[`${key}_total`];
    total += typeof declaredTotal === "number" && Number.isFinite(declaredTotal)
      ? declaredTotal
      : value.length;
  }
  return { facts, total };
}

function subjectLine(subjects: string[]): string {
  const count = subjects.length;
  const noun = count === 1 ? "page" : "pages";
  const head = subjects[0] ?? "";
  const rest = count > 1 ? ` +${count - 1}` : "";
  return `${count} ${noun} · ${head}${rest}`;
}

export function ActionCard({
  card,
  group,
  results,
}: {
  card: TechnicalAuditActionCard;
  group: TechnicalAuditFindingGroup | undefined;
  results: TechnicalAuditResult[];
}) {
  const representative = results[0];
  const subjects = group?.subjects ?? results.map((item) => item.subject);
  const statusColor = TECHNICAL_AUDIT_STATUS_COLOR[group?.status ?? "fail"];
  const nextAction = representative?.next_action;
  const { facts, total: factsTotal } = observedFacts(card.copy_values);
  const shownFacts = facts.slice(0, FACT_LIMIT);

  const lifecycle = results.find(
    (item) => item.lifecycle_state === "regressed",
  )?.lifecycle_state ?? representative?.lifecycle_state;
  const regressed = lifecycle === "regressed";

  return (
    <div
      className="mb-2.5 border p-4"
      style={{
        background: "var(--ink-soft)",
        borderColor: regressed ? "rgba(232, 154, 160, 0.4)" : "var(--hair)",
      }}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <div
            data-testid="card-title"
            className="font-serif text-[15px]"
            style={{ color: "var(--white)" }}
          >
            {findingTitle(group?.check_id, card.title)}
          </div>
          <div
            data-testid="card-subjects"
            className="mt-1 break-all font-mono text-[9px]"
            style={{ color: "var(--faint)" }}
          >
            {subjectLine(subjects)}
          </div>
        </div>
        <div className="flex shrink-0 gap-1.5">
          <span className={CHIP} style={{ color: statusColor, borderColor: statusColor }}>
            {TECHNICAL_AUDIT_STATUS_LABEL[group?.status ?? "fail"]}
          </span>
          {lifecycle && (
            <span
              className={CHIP}
              style={{
                color: LIFECYCLE_COLOR[lifecycle as TechnicalAuditLifecycleState],
                borderColor: LIFECYCLE_COLOR[lifecycle as TechnicalAuditLifecycleState],
              }}
            >
              {LIFECYCLE_LABEL[lifecycle as TechnicalAuditLifecycleState]}
            </span>
          )}
        </div>
      </div>

      <div className="my-3 px-3 py-3" style={{ background: "var(--ink)" }}>
        <div className="grid gap-y-2" style={{ gridTemplateColumns: "76px 1fr" }}>
          <div className={LABEL} style={{ color: "var(--faint)" }}>
            Now
          </div>
          <div className="font-serif text-[13px]" style={{ color: "var(--neg)" }}>
            {facts.length > 0 ? (
              <>
                <ul data-testid="card-facts" className="space-y-0.5">
                  {shownFacts.map((fact, i) => (
                    // Index-qualified: one page can link to the same dead URL
                    // twice (nav and footer), so facts are not unique.
                    <li key={`${i}-${fact}`} className="break-all font-mono text-[11px]">
                      {fact}
                    </li>
                  ))}
                </ul>
                {factsTotal > shownFacts.length && (
                  <div
                    data-testid="card-facts-remainder"
                    className={`${LABEL} mt-1.5`}
                    style={{ color: "var(--faint)" }}
                  >
                    Showing {shownFacts.length} of {factsTotal}
                  </div>
                )}
              </>
            ) : representative?.summary === GENERIC_UNKNOWN_SUMMARY ? (
              // The title already names the check; don't echo the generic
              // placeholder here. State the honest current condition instead.
              "Not yet measured"
            ) : (
              representative?.summary ?? card.title
            )}
          </div>
          <div className={LABEL} style={{ color: "var(--faint)" }}>
            Expected
          </div>
          <div
            data-testid="card-expected"
            className="font-serif text-[13px]"
            style={{ color: "var(--mute)" }}
          >
            {representative?.expected ?? "-"}
          </div>
          {nextAction?.instruction && (
            <>
              <div className={LABEL} style={{ color: "var(--faint)" }}>
                Next
              </div>
              <div data-testid="card-next-action" className="font-serif text-[13px]" style={{ color: "var(--white)" }}>
                {nextAction.instruction}
                <span className="font-mono text-[9px]" style={{ color: "var(--faint)" }}>
                  {" "}
                  · owner: {nextAction.owner}
                </span>
              </div>
            </>
          )}
        </div>
      </div>

      {card.instructions.length > 0 && (
        <details>
          <summary
            className={`${LABEL} cursor-pointer py-1`}
            style={{ color: "var(--faint)" }}
          >
            How to apply · {card.platform}
          </summary>
          <ol
            className="ml-4 mt-2 list-decimal space-y-1 font-serif text-[13px] leading-relaxed"
            style={{ color: "var(--mute)" }}
          >
            {card.instructions.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </details>
      )}

      <details>
        <summary
          className={`${LABEL} cursor-pointer py-1`}
          style={{ color: "var(--faint)" }}
        >
          Evidence · {results.length} findings
        </summary>
        <pre
          className="mt-2 overflow-x-auto whitespace-pre-wrap break-words font-mono text-[10px] leading-relaxed"
          style={{ color: "var(--mute)" }}
        >
          {JSON.stringify(
            results.map((item) => ({ subject: item.subject, observed: item.observed })),
            null,
            2,
          )}
        </pre>
      </details>

      <div
        className="mt-3 flex flex-wrap items-center gap-3 border-t pt-3"
        style={{ borderColor: "var(--hair)" }}
      >
        <CardActions cardId={card.id} status={card.status} />
        <span className={LABEL} style={{ color: "var(--faint)" }}>
          {CARD_STATUS_LABEL[card.status]}
        </span>
      </div>
    </div>
  );
}
