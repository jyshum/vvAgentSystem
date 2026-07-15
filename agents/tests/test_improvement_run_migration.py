from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase" / "migrations" / "015_improvement_run_mode.sql"
CANONICAL_SCHEMA = ROOT / "supabase" / "schema.sql"


def test_migration_remains_additive_for_existing_improvement_runs():
    sql = " ".join(MIGRATION.read_text().lower().split())

    assert "add column if not exists run_mode text not null default 'legacy'" in sql
    assert (
        "add column if not exists effective_check_sets text[] not null "
        "default '{}'::text[]"
    ) in sql


def test_historical_migration_defines_immutable_safe_run_routing():
    sql = " ".join(MIGRATION.read_text().lower().split())

    assert "run_mode text not null default 'legacy'" in sql
    assert "constraint improvement_runs_run_mode_check" in sql
    assert "check (run_mode in ('legacy', 'technical_v1'))" in sql
    assert "effective_check_sets text[] not null default '{}'::text[]" in sql
    assert "constraint improvement_runs_check_sets_match_mode_check" in sql
    assert "cardinality(effective_check_sets)" in sql
    assert (
        "create or replace function public.prevent_improvement_run_route_mutation()"
        in sql
    )
    assert "create trigger improvement_runs_route_controls_immutable" in sql
    assert "before update of run_mode, effective_check_sets" in sql
    assert "old.run_mode is distinct from new.run_mode" in sql
    assert (
        "old.effective_check_sets is distinct from new.effective_check_sets"
        in sql
    )
    assert "comment on column public.improvement_runs.run_mode is" in sql
    assert "'immutable route selected when the improvement run was inserted.'" in sql
    assert "comment on column public.improvement_runs.effective_check_sets is" in sql
    assert (
        "'immutable technical check sets selected when the improvement run was inserted.'"
        in sql
    )


def test_canonical_schema_reflects_post_cleanup_runtime():
    sql = " ".join(CANONICAL_SCHEMA.read_text().lower().split())
    clients = sql.split("create table public.clients (", 1)[1].split(");", 1)[0]
    pipeline_runs = sql.split("create table public.pipeline_runs (", 1)[1].split(");", 1)[0]
    improvement_runs = sql.split("create table public.improvement_runs (", 1)[1].split(");", 1)[0]

    assert "site_platform text not null default 'unknown'" in clients
    assert "implementation_mode text not null default 'copy_paste'" in clients
    for column in (
        "cycle_frequency",
        "cycle_day",
        "cms_type",
        "cms_config",
        "auto_approve_action_types",
    ):
        assert column not in clients

    assert "check (status in ('running', 'completed', 'error'))" in pipeline_runs
    assert "awaiting_approval" not in pipeline_runs
    assert "implementing" not in pipeline_runs

    for column in (
        "crawlability_report",
        "pages_inventoried",
        "queries_matched",
        "content_gaps_found",
        "cards_generated",
        "run_mode",
        "effective_check_sets",
    ):
        assert column not in improvement_runs

    for table in (
        "action_cards",
        "page_citation_scores",
        "query_page_matches",
        "page_inventory",
        "client_site_profiles",
    ):
        assert f"create table public.{table}" not in sql
        assert f"alter table public.{table}" not in sql
        assert f" on public.{table}" not in sql

    for preserved_table in (
        "clients",
        "client_users",
        "queries",
        "tracker_runs",
        "pipeline_runs",
        "improvement_runs",
        "technical_audit_runs",
    ):
        assert f"create table public.{preserved_table}" in sql

    assert "create or replace function public.prevent_improvement_run_route_mutation()" not in sql
    assert "create trigger improvement_runs_route_controls_immutable" not in sql
