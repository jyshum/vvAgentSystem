import { createAdminClient } from "@/lib/supabase/admin";
import { ApprovalsClient } from "@/components/admin/ApprovalsClient";

export default async function ApprovalsPage() {
  const supabase = createAdminClient();

  const { data: cards } = await supabase
    .from("action_cards")
    .select("id, page_url, pillar, score, issue, before_text, after_text, code_block, status, cms_action, run_id")
    .eq("status", "pending")
    .order("score", { ascending: true });

  // Get client names for the cards via audit_runs
  const runIds = [...new Set((cards || []).map(c => c.run_id).filter(Boolean))];
  let clientMap: Record<string, string> = {};
  if (runIds.length > 0) {
    const { data: runs } = await supabase
      .from("audit_runs")
      .select("id, client_id, clients(brand_name)")
      .in("id", runIds);
    for (const run of runs || []) {
      const brandName = (run as any).clients?.brand_name || "Unknown";
      clientMap[run.id] = brandName;
    }
  }

  const enrichedCards = (cards || []).map(c => ({
    ...c,
    client_name: clientMap[c.run_id] || "Unknown",
    before_text: c.before_text || "",
    after_text: c.after_text || "",
    code_block: c.code_block || "",
    cms_action: c.cms_action || "",
  }));

  const { data: pipelineRuns } = await supabase
    .from("pipeline_runs")
    .select("thread_id, client_id")
    .eq("status", "awaiting_approval");

  return (
    <div>
      <h1
        className="font-display text-[52px] font-light leading-[0.96] mb-2"
        style={{ color: "var(--white)" }}
      >
        Approvals
      </h1>
      <p className="font-serif italic text-base mb-10" style={{ color: "var(--mute)" }}>
        {enrichedCards.length} pending action card{enrichedCards.length !== 1 ? "s" : ""}
      </p>
      <ApprovalsClient
        initialCards={enrichedCards}
        pipelineRuns={pipelineRuns || []}
      />
    </div>
  );
}
