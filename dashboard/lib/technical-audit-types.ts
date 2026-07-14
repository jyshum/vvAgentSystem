export type TechnicalAuditStatus =
  | "pass"
  | "fail"
  | "review"
  | "unknown"
  | "not_applicable";

export type TechnicalAuditConfidence = "high" | "medium" | "low";

export interface TechnicalAuditSummary {
  pass: number;
  fail: number;
  review: number;
  unknown: number;
  not_applicable: number;
  total: number;
}

export interface TechnicalAuditRun {
  id: string;
  client_id: string;
  improvement_run_id: string | null;
  pipeline_run_id: string | null;
  audit_version: number;
  status: "running" | "completed" | "error";
  scope: Record<string, unknown>;
  summary: TechnicalAuditSummary;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface TechnicalAuditResult {
  id: string;
  audit_run_id: string;
  check_id: string;
  check_version: number;
  section: string;
  subject: string;
  status: TechnicalAuditStatus;
  severity: string;
  summary: string;
  expected: string;
  observed: Record<string, unknown>;
  evidence_refs: string[];
  scope: Record<string, unknown>;
  applicability: { applies: boolean; reason: string };
  confidence: TechnicalAuditConfidence;
  next_action: { owner: string; instruction: string };
  remediation_id: string | null;
  lifecycle_state: "new" | "continuing" | "changed" | "resolved" | "regressed";
  created_at: string;
}

export const TECHNICAL_AUDIT_STATUS_ORDER: TechnicalAuditStatus[] = [
  "fail",
  "review",
  "unknown",
  "pass",
  "not_applicable",
];

export const TECHNICAL_AUDIT_STATUS_LABEL: Record<TechnicalAuditStatus, string> = {
  pass: "pass",
  fail: "fail",
  review: "review",
  unknown: "unknown",
  not_applicable: "not applicable",
};

export const TECHNICAL_AUDIT_STATUS_COLOR: Record<TechnicalAuditStatus, string> = {
  pass: "var(--pos)",
  fail: "var(--neg)",
  review: "#d4a017",
  unknown: "var(--mute)",
  not_applicable: "var(--faint)",
};
