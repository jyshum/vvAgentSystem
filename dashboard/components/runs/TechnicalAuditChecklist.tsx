import {
  TECHNICAL_AUDIT_STATUS_COLOR,
  TECHNICAL_AUDIT_STATUS_LABEL,
  TECHNICAL_AUDIT_STATUS_ORDER,
  type TechnicalAuditResult,
  type TechnicalAuditRun,
  type TechnicalAuditStatus,
} from "@/lib/technical-audit-types";

function sectionLabel(section: string): string {
  return section.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function statusCount(run: TechnicalAuditRun, status: TechnicalAuditStatus): number {
  return run.summary?.[status] ?? 0;
}

function ResultRow({ result }: { result: TechnicalAuditResult }) {
  const needsAttention = ["fail", "review", "unknown"].includes(result.status);
  const color = TECHNICAL_AUDIT_STATUS_COLOR[result.status];

  return (
    <details
      open={needsAttention}
      className="border-t first:border-t-0"
      style={{ borderColor: "var(--hair)" }}
    >
      <summary className="cursor-pointer list-none px-4 py-3">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="font-serif text-[15px]" style={{ color: "var(--white)" }}>
              {result.summary}
            </div>
            <div className="mt-1 break-all font-mono text-[9px]" style={{ color: "var(--faint)" }}>
              {result.subject}
            </div>
          </div>
          <span
            className="shrink-0 border px-2 py-1 font-mono text-[8px] uppercase tracking-[0.12em]"
            style={{ color, borderColor: color }}
          >
            {TECHNICAL_AUDIT_STATUS_LABEL[result.status]}
          </span>
        </div>
      </summary>

      <div
        className="grid gap-px border-t md:grid-cols-2"
        style={{ background: "var(--hair)", borderColor: "var(--hair)" }}
      >
        <EvidenceField label="Expected" value={result.expected} />
        <EvidenceField label="Why this applies" value={result.applicability.reason} />
        <EvidenceField
          label="Next action"
          value={`${result.next_action.instruction} · owner: ${result.next_action.owner}`}
        />
        <EvidenceField
          label="Scope"
          value={`${JSON.stringify(result.scope)} · confidence: ${result.confidence}`}
        />
        <div className="md:col-span-2 px-4 py-3" style={{ background: "var(--ink-soft)" }}>
          <div className="mb-1.5 font-mono text-[8px] uppercase tracking-[0.12em]" style={{ color: "var(--faint)" }}>
            Observed evidence
          </div>
          <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-[10px] leading-relaxed" style={{ color: "var(--mute)" }}>
            {JSON.stringify(result.observed, null, 2)}
          </pre>
        </div>
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

export function TechnicalAuditChecklist({
  run,
  results,
}: {
  run: TechnicalAuditRun;
  results: TechnicalAuditResult[];
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
            : "Evidence is still being collected. Checklist counts will appear after completion."}
        </p>
      </section>
    );
  }

  const sections = new Map<string, TechnicalAuditResult[]>();
  for (const result of results) {
    const sectionResults = sections.get(result.section) ?? [];
    sectionResults.push(result);
    sections.set(result.section, sectionResults);
  }

  return (
    <section className="mb-8">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-[28px] font-light" style={{ color: "var(--white)" }}>
            Technical audit
          </h2>
          <div className="font-mono text-[8px] uppercase tracking-[0.12em]" style={{ color: "var(--faint)" }}>
            Checklist v{run.audit_version} · {run.summary.total} checks
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {TECHNICAL_AUDIT_STATUS_ORDER.map((status) => (
            <span
              key={status}
              className="border px-2 py-1 font-mono text-[8px] uppercase tracking-[0.1em]"
              style={{
                color: TECHNICAL_AUDIT_STATUS_COLOR[status],
                borderColor: TECHNICAL_AUDIT_STATUS_COLOR[status],
              }}
            >
              {statusCount(run, status)} {TECHNICAL_AUDIT_STATUS_LABEL[status]}
            </span>
          ))}
        </div>
      </div>

      <div className="border" style={{ borderColor: "var(--hair)" }}>
        {[...sections.entries()].map(([section, sectionResults]) => {
          const attention = sectionResults.some((result) =>
            ["fail", "review", "unknown"].includes(result.status),
          );
          return (
            <details key={section} open={attention} className="border-b last:border-b-0" style={{ borderColor: "var(--hair)" }}>
              <summary
                className="cursor-pointer px-4 py-3 font-mono text-[9px] uppercase tracking-[0.12em]"
                style={{ color: "var(--mute)", background: "var(--ink-2)" }}
              >
                {sectionLabel(section)} · {sectionResults.length}
              </summary>
              <div style={{ background: "var(--ink)" }}>
                {sectionResults.map((result) => (
                  <ResultRow key={result.id} result={result} />
                ))}
              </div>
            </details>
          );
        })}
      </div>
    </section>
  );
}
