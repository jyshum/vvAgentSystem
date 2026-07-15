import { TechnicalAuditChecklist } from "@/components/runs/TechnicalAuditChecklist";
import type { RunPresentationMode } from "@/lib/run-presentation";
import type {
  TechnicalAuditResult,
  TechnicalAuditRun,
} from "@/lib/technical-audit-types";

export function RunTechnicalAuditEvidence({
  mode,
  run,
  results,
}: {
  mode: RunPresentationMode;
  run: TechnicalAuditRun | null;
  results: TechnicalAuditResult[];
}) {
  if (!run) return null;

  return (
    <>
      {mode === "legacy" && (
        <div
          className="mb-3 font-mono text-[9px] uppercase tracking-[0.14em]"
          style={{ color: "var(--faint)" }}
        >
          HISTORICAL TECHNICAL CHECKLIST
        </div>
      )}
      <TechnicalAuditChecklist run={run} results={results} />
    </>
  );
}
