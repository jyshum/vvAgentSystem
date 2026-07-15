from pathlib import Path


MIGRATION = Path(__file__).parents[2] / "supabase/migrations/016_unified_manual_client_config.sql"


def test_unified_config_is_additive_and_backfills_budgetyourmd():
    sql = MIGRATION.read_text()
    assert "add column if not exists site_platform" in sql.lower()
    assert "add column if not exists implementation_mode" in sql.lower()
    assert "lower(website_domain) = 'budgetyourmd.ca'" in sql.lower()
    assert "site_platform = 'squarespace'" in sql.lower()
    assert "implementation_mode = 'copy_paste'" in sql.lower()
    assert "drop column" not in sql.lower()


def test_cleanup_drops_only_approved_legacy_contracts():
    sql = (
        Path(__file__).parents[2]
        / "supabase/migrations/017_remove_legacy_runtime.sql"
    ).read_text().lower()
    for table in (
        "action_cards",
        "page_citation_scores",
        "query_page_matches",
        "page_inventory",
        "client_site_profiles",
    ):
        assert f"drop table if exists public.{table}" in sql
    for column in (
        "cycle_frequency",
        "cycle_day",
        "cms_type",
        "cms_config",
        "auto_approve_action_types",
    ):
        assert f"drop column if exists {column}" in sql
    assert "drop table public.tracker_runs" not in sql
    assert "drop table public.queries" not in sql
    assert "drop table public.technical_audit_runs" not in sql
