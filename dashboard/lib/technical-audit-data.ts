import { createAdminClient } from "@/lib/supabase/admin";
import type {
  TechnicalAuditActionCard,
  TechnicalAuditFindingGroup,
  TechnicalAuditResult,
  TechnicalAuditRun,
} from "@/lib/technical-audit-types";

export interface AuditTabData {
  run: TechnicalAuditRun | null;
  runs: Pick<TechnicalAuditRun, "id" | "status" | "started_at">[];
  results: TechnicalAuditResult[];
  groups: TechnicalAuditFindingGroup[];
  cards: TechnicalAuditActionCard[];
}

/** Loads everything the AUDIT tab renders for one run.
 *  `runId` omitted means the latest run for the client. */
export async function loadAuditTabData(
  clientId: string,
  runId?: string,
): Promise<AuditTabData> {
  const supabase = createAdminClient();

  const { data: runList } = await supabase
    .from("technical_audit_runs")
    .select("id, status, started_at")
    .eq("client_id", clientId)
    .order("started_at", { ascending: false })
    .limit(20);

  const runs = (runList as AuditTabData["runs"]) ?? [];
  const targetId = runId ?? runs[0]?.id;
  if (!targetId) {
    return { run: null, runs, results: [], groups: [], cards: [] };
  }

  const { data: run } = await supabase
    .from("technical_audit_runs")
    .select("*")
    .eq("id", targetId)
    .eq("client_id", clientId)
    .maybeSingle();

  if (!run) {
    return { run: null, runs, results: [], groups: [], cards: [] };
  }

  const [resultsRes, groupsRes, cardsRes] = await Promise.all([
    supabase
      .from("technical_audit_results")
      .select("*")
      .eq("audit_run_id", targetId)
      .order("section")
      .order("check_id")
      .order("subject"),
    supabase
      .from("technical_audit_finding_groups")
      .select("*")
      .eq("audit_run_id", targetId),
    supabase
      .from("technical_audit_action_cards")
      .select("*")
      .eq("audit_run_id", targetId)
      .order("created_at", { ascending: true }),
  ]);

  return {
    run: run as TechnicalAuditRun,
    runs,
    results: (resultsRes.data as TechnicalAuditResult[]) ?? [],
    groups: (groupsRes.data as TechnicalAuditFindingGroup[]) ?? [],
    cards: (cardsRes.data as TechnicalAuditActionCard[]) ?? [],
  };
}

/** Counts results by lifecycle_state for the strip. Returns only non-zero
 *  states so the strip stays quiet when nothing changed. */
export function lifecycleCounts(
  results: TechnicalAuditResult[],
): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const result of results) {
    if (!result.lifecycle_state) continue;
    counts[result.lifecycle_state] = (counts[result.lifecycle_state] ?? 0) + 1;
  }
  return counts;
}
