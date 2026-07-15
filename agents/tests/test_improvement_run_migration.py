from pathlib import Path

import pytest


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


@pytest.mark.parametrize("sql_path", [MIGRATION, CANONICAL_SCHEMA])
def test_sql_sources_define_immutable_historical_safe_run_routing(sql_path):
    assert sql_path.exists(), f"missing SQL source: {sql_path}"
    sql = " ".join(sql_path.read_text().lower().split())

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


def test_canonical_schema_orders_route_contract_for_idempotent_fresh_install():
    sql = " ".join(CANONICAL_SCHEMA.read_text().lower().split())

    assert (
        "drop function if exists public.prevent_improvement_run_route_mutation() cascade"
        in sql
    )
    table_position = sql.index("create table public.improvement_runs")
    function_position = sql.index(
        "create or replace function public.prevent_improvement_run_route_mutation()"
    )
    trigger_position = sql.index(
        "create trigger improvement_runs_route_controls_immutable"
    )
    assert table_position < function_position < trigger_position
