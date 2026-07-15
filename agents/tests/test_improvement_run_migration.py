from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "015_improvement_run_mode.sql"
)


def test_migration_adds_immutable_historical_safe_run_routing_fields():
    assert MIGRATION.exists(), "migration 015 must persist improvement-run routing"
    sql = " ".join(MIGRATION.read_text().lower().split())

    assert "add column if not exists run_mode text not null default 'legacy'" in sql
    assert "check (run_mode in ('legacy', 'technical_v1'))" in sql
    assert (
        "add column if not exists effective_check_sets text[] not null "
        "default '{}'::text[]"
    ) in sql
    assert "cardinality(effective_check_sets)" in sql
    assert "before update of run_mode, effective_check_sets" in sql
    assert "old.run_mode is distinct from new.run_mode" in sql
    assert (
        "old.effective_check_sets is distinct from new.effective_check_sets"
        in sql
    )
