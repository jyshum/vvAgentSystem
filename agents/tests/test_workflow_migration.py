from pathlib import Path

MIGRATION = (
    Path(__file__).parents[2] / "supabase/migrations/018_technical_audit_workflow.sql"
)


def test_workflow_migration_is_additive_and_complete():
    sql = MIGRATION.read_text().lower()
    assert "add column if not exists finding_key" in sql
    for table in (
        "technical_audit_finding_groups",
        "technical_audit_action_cards",
        "technical_audit_card_results",
    ):
        assert f"create table public.{table}" in sql
        assert f"alter table public.{table} enable row level security" in sql
    assert "drop table" not in sql
    assert "drop column" not in sql
    # No legacy surface returns.
    for legacy in ("page_citation_scores", "query_page_matches", "page_inventory",
                   "client_site_profiles", "cycle_frequency"):
        assert legacy not in sql


def test_card_states_match_workflow_contract():
    sql = MIGRATION.read_text().lower()
    for state in ("observed", "draft_prepared", "approved", "rejected",
                  "applied", "verified", "still_failing", "stale"):
        assert f"'{state}'" in sql
    assert "'publishing'" not in sql
