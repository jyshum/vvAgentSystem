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

export type TechnicalAuditLifecycleState =
  | "new"
  | "continuing"
  | "changed"
  | "resolved"
  | "regressed";

export type TechnicalAuditCardStatus =
  | "observed"
  | "draft_prepared"
  | "approved"
  | "rejected"
  | "applied"
  | "verified"
  | "still_failing"
  | "stale";

export interface TechnicalAuditFindingGroup {
  id: string;
  audit_run_id: string;
  group_key: string;
  check_id: string;
  remediation_id: string | null;
  summary: string;
  status: "fail" | "review" | "unknown";
  subjects: string[];
  created_at: string;
}

export interface TechnicalAuditActionCard {
  id: string;
  client_id: string;
  audit_run_id: string;
  group_key: string | null;
  source: "technical" | "community";
  status: TechnicalAuditCardStatus;
  title: string;
  platform: string;
  implementation_mode: string;
  instructions: string[];
  copy_values: Record<string, unknown>;
  precondition: Record<string, unknown>;
  approved_by: string | null;
  approved_at: string | null;
  applied_at: string | null;
  verification: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

/** Mirrors ALLOWED_TRANSITIONS in agents/src/technical_audit/workflow.py.
 *  The backend is authoritative; this only decides which buttons to render,
 *  so the UI never offers an action the state machine would reject. */
export const CARD_ALLOWED_TRANSITIONS: Record<
  TechnicalAuditCardStatus,
  TechnicalAuditCardStatus[]
> = {
  observed: ["draft_prepared", "rejected"],
  draft_prepared: ["approved", "rejected"],
  approved: ["applied", "rejected", "stale"],
  applied: ["verified", "still_failing"],
  stale: ["draft_prepared", "rejected"],
  rejected: [],
  verified: [],
  still_failing: ["draft_prepared", "rejected"],
};

export const CARD_STATUS_LABEL: Record<TechnicalAuditCardStatus, string> = {
  observed: "observed",
  draft_prepared: "draft prepared",
  approved: "approved",
  rejected: "rejected",
  applied: "applied",
  verified: "verified",
  still_failing: "still failing",
  stale: "stale",
};

export const LIFECYCLE_LABEL: Record<TechnicalAuditLifecycleState, string> = {
  new: "new",
  continuing: "continuing",
  changed: "changed",
  resolved: "resolved",
  regressed: "regressed",
};

export const LIFECYCLE_COLOR: Record<TechnicalAuditLifecycleState, string> = {
  new: "var(--white)",
  continuing: "var(--mute)",
  changed: "var(--mute)",
  resolved: "var(--pos)",
  regressed: "var(--neg)",
};

/** Order for the lifecycle strip. Regressed leads: a fix that broke again is
 *  the one fact nothing else in the product reports. `continuing` is
 *  intentionally excluded: it means no material change, so it is not news. */
export const LIFECYCLE_STRIP_ORDER: TechnicalAuditLifecycleState[] = [
  "regressed",
  "new",
  "resolved",
  "changed",
];
