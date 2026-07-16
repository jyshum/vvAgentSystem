import {
  TECHNICAL_AUDIT_STATUS_COLOR,
  TECHNICAL_AUDIT_STATUS_LABEL,
  TECHNICAL_AUDIT_STATUS_ORDER,
  type TechnicalAuditRun,
} from "@/lib/technical-audit-types";
import { RunAuditButton } from "@/components/audit/RunAuditButton";

export function AuditSummary({
  run,
  clientId,
  domain,
}: {
  run: TechnicalAuditRun;
  clientId: string;
  domain: string;
}) {
  return (
    <div className="mb-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-[30px] font-light" style={{ color: "var(--white)" }}>
            Technical audit
          </h1>
          <div
            data-testid="audit-meta"
            className="mt-1 font-mono text-[8px] uppercase tracking-[0.12em]"
            style={{ color: "var(--faint)" }}
          >
            v{run.audit_version} · {run.summary.total} checks · {domain}
          </div>
        </div>
        <RunAuditButton clientId={clientId} />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {TECHNICAL_AUDIT_STATUS_ORDER.map((status) => (
          <span
            key={status}
            className="border px-2 py-1 font-mono text-[8px] uppercase tracking-[0.1em]"
            style={{
              color: TECHNICAL_AUDIT_STATUS_COLOR[status],
              borderColor: TECHNICAL_AUDIT_STATUS_COLOR[status],
            }}
          >
            {run.summary[status] ?? 0} {TECHNICAL_AUDIT_STATUS_LABEL[status]}
          </span>
        ))}
      </div>
    </div>
  );
}
