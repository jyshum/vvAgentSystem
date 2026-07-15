-- Persist the route decision that created each improvement run.
-- Existing rows predate this discriminator and remain legacy regardless of
-- whether a technical_audit_runs child happens to exist.

alter table public.improvement_runs
  add column if not exists run_mode text not null default 'legacy',
  add column if not exists effective_check_sets text[] not null default '{}'::text[];

alter table public.improvement_runs
  add constraint improvement_runs_run_mode_check
    check (run_mode in ('legacy', 'technical_v1')),
  add constraint improvement_runs_check_sets_match_mode_check
    check (
      (run_mode = 'legacy' and cardinality(effective_check_sets) = 0)
      or
      (run_mode = 'technical_v1' and cardinality(effective_check_sets) > 0)
    );

create or replace function public.prevent_improvement_run_route_mutation()
returns trigger
language plpgsql
as $$
begin
  if old.run_mode is distinct from new.run_mode
    or old.effective_check_sets is distinct from new.effective_check_sets then
    raise exception 'improvement run route controls are immutable';
  end if;
  return new;
end;
$$;

create trigger improvement_runs_route_controls_immutable
  before update of run_mode, effective_check_sets
  on public.improvement_runs
  for each row
  execute function public.prevent_improvement_run_route_mutation();

comment on column public.improvement_runs.run_mode is
  'Immutable route selected when the improvement run was inserted.';
comment on column public.improvement_runs.effective_check_sets is
  'Immutable technical check sets selected when the improvement run was inserted.';
