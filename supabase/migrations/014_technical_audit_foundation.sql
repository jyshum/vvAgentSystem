-- 014_technical_audit_foundation.sql
-- Additive, versioned storage for evidence-backed technical checklist runs.
-- Legacy page_citation_scores and action_cards remain unchanged.

create table public.client_site_profiles (
  client_id uuid primary key references public.clients(id) on delete cascade,
  audit_version integer not null default 1 check (audit_version > 0),
  llms_txt_enabled boolean not null default false,
  priority_urls text[] not null default '{}',
  platform text not null default 'unknown'
    check (platform in ('unknown', 'github', 'wordpress', 'webflow', 'squarespace', 'other')),
  integration_state jsonb not null default '{}'::jsonb,
  verified_facts jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table public.technical_audit_runs (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  improvement_run_id uuid references public.improvement_runs(id) on delete set null,
  pipeline_run_id uuid references public.pipeline_runs(id) on delete set null,
  audit_version integer not null check (audit_version > 0),
  status text not null default 'running'
    check (status in ('running', 'completed', 'error')),
  scope jsonb not null default '{}'::jsonb,
  summary jsonb not null default '{}'::jsonb,
  error_message text,
  started_at timestamptz not null default now(),
  completed_at timestamptz
);

create table public.technical_audit_observations (
  id uuid primary key default gen_random_uuid(),
  audit_run_id uuid not null references public.technical_audit_runs(id) on delete cascade,
  observation_ref text not null,
  kind text not null,
  subject text not null,
  retrieved_at timestamptz not null,
  fingerprint text not null check (char_length(fingerprint) = 64),
  data jsonb not null default '{}'::jsonb
    check (octet_length(data::text) <= 65536),
  unique (audit_run_id, observation_ref)
);

create table public.technical_audit_results (
  id uuid primary key default gen_random_uuid(),
  audit_run_id uuid not null references public.technical_audit_runs(id) on delete cascade,
  check_id text not null,
  check_version integer not null check (check_version > 0),
  section text not null,
  subject text not null,
  status text not null
    check (status in ('pass', 'fail', 'review', 'unknown', 'not_applicable')),
  severity text not null,
  summary text not null,
  expected text not null,
  observed jsonb not null default '{}'::jsonb,
  evidence_refs text[] not null default '{}',
  scope jsonb not null default '{}'::jsonb,
  applicability jsonb not null,
  confidence text not null check (confidence in ('high', 'medium', 'low')),
  next_action jsonb not null,
  remediation_id text,
  lifecycle_state text not null default 'new'
    check (lifecycle_state in ('new', 'continuing', 'changed', 'resolved', 'regressed')),
  created_at timestamptz not null default now(),
  unique (audit_run_id, check_id, check_version, subject)
);

create index idx_client_site_profiles_platform
  on public.client_site_profiles(platform);
create index idx_technical_audit_runs_client_id
  on public.technical_audit_runs(client_id);
create index idx_technical_audit_runs_improvement_run_id
  on public.technical_audit_runs(improvement_run_id);
create index idx_technical_audit_runs_pipeline_run_id
  on public.technical_audit_runs(pipeline_run_id);
create index idx_technical_audit_observations_run_id
  on public.technical_audit_observations(audit_run_id);
create index idx_technical_audit_results_run_id
  on public.technical_audit_results(audit_run_id);
create index idx_technical_audit_results_status
  on public.technical_audit_results(status);
create index idx_technical_audit_results_section
  on public.technical_audit_results(section);

alter table public.client_site_profiles enable row level security;
alter table public.technical_audit_runs enable row level security;
alter table public.technical_audit_observations enable row level security;
alter table public.technical_audit_results enable row level security;

create policy "Admins manage client_site_profiles" on public.client_site_profiles
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Clients view own site profile" on public.client_site_profiles
  for select using (client_id = public.get_my_client_id());

create policy "Admins manage technical_audit_runs" on public.technical_audit_runs
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Clients view own technical_audit_runs" on public.technical_audit_runs
  for select using (client_id = public.get_my_client_id());

create policy "Admins manage technical_audit_observations" on public.technical_audit_observations
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Clients view own technical_audit_observations" on public.technical_audit_observations
  for select using (
    exists (
      select 1 from public.technical_audit_runs run
      where run.id = audit_run_id
        and run.client_id = public.get_my_client_id()
    )
  );

create policy "Admins manage technical_audit_results" on public.technical_audit_results
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Clients view own technical_audit_results" on public.technical_audit_results
  for select using (
    exists (
      select 1 from public.technical_audit_runs run
      where run.id = audit_run_id
        and run.client_id = public.get_my_client_id()
    )
  );
