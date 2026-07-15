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
