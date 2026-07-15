-- 018_technical_audit_workflow.sql
-- Finding lifecycle keys, deterministic finding groups, and the unified
-- action-card workflow over immutable technical audit results.
-- Additive only: no legacy tables are recreated and no evidence is mutated.

alter table public.technical_audit_results
  add column if not exists finding_key text;

create index if not exists idx_technical_audit_results_finding_key
  on public.technical_audit_results(finding_key);

create table public.technical_audit_finding_groups (
  id uuid primary key default gen_random_uuid(),
  audit_run_id uuid not null references public.technical_audit_runs(id) on delete cascade,
  group_key text not null,
  check_id text not null,
  remediation_id text,
  summary text not null,
  status text not null
    check (status in ('fail', 'review', 'unknown')),
  subjects text[] not null default '{}',
  created_at timestamptz not null default now(),
  unique (audit_run_id, group_key)
);

create table public.technical_audit_action_cards (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  audit_run_id uuid not null references public.technical_audit_runs(id) on delete cascade,
  group_key text,
  source text not null default 'technical'
    check (source in ('technical', 'community')),
  status text not null default 'observed'
    check (status in (
      'observed', 'draft_prepared', 'approved', 'rejected',
      'applied', 'verified', 'still_failing', 'stale')),
  title text not null,
  platform text not null,
  implementation_mode text not null,
  instructions jsonb not null default '[]'::jsonb,
  copy_values jsonb not null default '{}'::jsonb,
  precondition jsonb not null default '{}'::jsonb,
  approved_by text,
  approved_at timestamptz,
  applied_at timestamptz,
  verification jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.technical_audit_card_results (
  card_id uuid not null references public.technical_audit_action_cards(id) on delete cascade,
  result_id uuid not null references public.technical_audit_results(id) on delete cascade,
  primary key (card_id, result_id)
);

create index idx_technical_audit_finding_groups_run_id
  on public.technical_audit_finding_groups(audit_run_id);
create index idx_technical_audit_action_cards_client_id
  on public.technical_audit_action_cards(client_id);
create index idx_technical_audit_action_cards_run_id
  on public.technical_audit_action_cards(audit_run_id);
create index idx_technical_audit_action_cards_status
  on public.technical_audit_action_cards(status);
create index idx_technical_audit_card_results_result_id
  on public.technical_audit_card_results(result_id);

alter table public.technical_audit_finding_groups enable row level security;
alter table public.technical_audit_action_cards enable row level security;
alter table public.technical_audit_card_results enable row level security;

create policy "Admins manage technical_audit_finding_groups" on public.technical_audit_finding_groups
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Clients view own technical_audit_finding_groups" on public.technical_audit_finding_groups
  for select using (
    exists (
      select 1 from public.technical_audit_runs run
      where run.id = audit_run_id
        and run.client_id = public.get_my_client_id()
    )
  );

create policy "Admins manage technical_audit_action_cards" on public.technical_audit_action_cards
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Clients view own technical_audit_action_cards" on public.technical_audit_action_cards
  for select using (client_id = public.get_my_client_id());

create policy "Admins manage technical_audit_card_results" on public.technical_audit_card_results
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Clients view own technical_audit_card_results" on public.technical_audit_card_results
  for select using (
    exists (
      select 1 from public.technical_audit_action_cards card
      where card.id = card_id
        and card.client_id = public.get_my_client_id()
    )
  );
