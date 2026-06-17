-- VV Client Dashboard — Initial Schema
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New query)

-- ══════════════════════════════════════════════
-- Tables
-- ══════════════════════════════════════════════

create table public.clients (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  brand_name text not null,
  website_domain text default '',
  brand_variations jsonb default '[]'::jsonb,
  target_queries jsonb default '[]'::jsonb,
  competitors jsonb default '[]'::jsonb,
  created_at timestamptz default now()
);

create table public.client_users (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  client_id uuid references public.clients(id) on delete cascade,
  role text not null check (role in ('admin', 'client')),
  created_at timestamptz default now(),
  unique (user_id)
);

create table public.tracker_runs (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  ran_at timestamptz default now(),
  aggregate_mention_rate float,
  aggregate_citation_rate float,
  per_engine_scores jsonb default '{}'::jsonb,
  competitor_scores jsonb default '{}'::jsonb
);

create table public.tracker_results (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.tracker_runs(id) on delete cascade,
  query text not null,
  engine text not null,
  model text default '',
  brand_mentioned boolean default false,
  brand_cited boolean default false,
  citation_url text,
  competitor_mentions jsonb default '[]'::jsonb,
  response_text text default '',
  queried_at timestamptz default now()
);

create table public.reports (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  run_id uuid references public.tracker_runs(id) on delete set null,
  week_start date not null,
  status text not null default 'draft' check (status in ('draft', 'published')),
  exec_summary text default '',
  work_completed jsonb default '[]'::jsonb,
  priorities jsonb default '[]'::jsonb,
  highlights jsonb default '[]'::jsonb,
  blockers jsonb default '[]'::jsonb,
  notes text default '',
  search_console jsonb,
  published_at timestamptz,
  created_at timestamptz default now()
);

-- ══════════════════════════════════════════════
-- View: tracker_results without response_text (for client access)
-- ══════════════════════════════════════════════

create view public.tracker_results_client as
select
  id, run_id, query, engine, model,
  brand_mentioned, brand_cited, citation_url,
  competitor_mentions, queried_at
from public.tracker_results;

-- ══════════════════════════════════════════════
-- Indexes
-- ══════════════════════════════════════════════

create index idx_client_users_user_id on public.client_users(user_id);
create index idx_client_users_client_id on public.client_users(client_id);
create index idx_tracker_runs_client_id on public.tracker_runs(client_id);
create index idx_tracker_results_run_id on public.tracker_results(run_id);
create index idx_reports_client_id on public.reports(client_id);
create index idx_reports_status on public.reports(status);

-- ══════════════════════════════════════════════
-- Helper function: get the client_id for the current auth user
-- ══════════════════════════════════════════════

create or replace function public.get_my_client_id()
returns uuid
language sql
stable
security definer
as $$
  select client_id from public.client_users
  where user_id = auth.uid()
  limit 1;
$$;

create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
as $$
  select exists (
    select 1 from public.client_users
    where user_id = auth.uid() and role = 'admin'
  );
$$;

-- ══════════════════════════════════════════════
-- Row Level Security
-- ══════════════════════════════════════════════

alter table public.clients enable row level security;
alter table public.client_users enable row level security;
alter table public.tracker_runs enable row level security;
alter table public.tracker_results enable row level security;
alter table public.reports enable row level security;

-- clients
create policy "Admins can do everything with clients"
  on public.clients for all
  using (public.is_admin())
  with check (public.is_admin());

create policy "Clients can view their own client record"
  on public.clients for select
  using (id = public.get_my_client_id());

-- client_users
create policy "Admins can manage client_users"
  on public.client_users for all
  using (public.is_admin())
  with check (public.is_admin());

create policy "Users can view their own client_users row"
  on public.client_users for select
  using (user_id = auth.uid());

-- tracker_runs
create policy "Admins can manage tracker_runs"
  on public.tracker_runs for all
  using (public.is_admin())
  with check (public.is_admin());

create policy "Clients can view their own tracker_runs"
  on public.tracker_runs for select
  using (client_id = public.get_my_client_id());

-- tracker_results (admins only — clients use the view)
create policy "Admins can manage tracker_results"
  on public.tracker_results for all
  using (public.is_admin())
  with check (public.is_admin());

-- reports
create policy "Admins can manage reports"
  on public.reports for all
  using (public.is_admin())
  with check (public.is_admin());

create policy "Clients can view their own published reports"
  on public.reports for select
  using (
    status = 'published'
    and client_id = public.get_my_client_id()
  );

-- Grant access to the client view
grant select on public.tracker_results_client to authenticated;

-- RLS-like filter on the view (views don't support RLS directly,
-- so we use a security definer function for filtering in queries)
-- Client-side queries should always filter:
--   WHERE run_id IN (SELECT id FROM tracker_runs WHERE client_id = get_my_client_id())
