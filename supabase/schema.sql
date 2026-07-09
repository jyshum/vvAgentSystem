-- ============================================================================
-- Victory Velocity — consolidated schema (current version, 2026-07-08)
-- ============================================================================
-- Single canonical baseline that replaces migrations 001–010. Paste the whole
-- file into the Supabase SQL editor and run once.
--
-- WARNING: the DROP block below DELETES ALL DATA in these tables (clients,
-- tracker history, reports, cards, etc.). Only run on a database you intend to
-- wipe.
--
-- What this keeps vs. drops relative to the old migrations:
--   KEPT:    clients, client_users, tracker_runs, tracker_results (+view),
--            reports, pipeline_runs, prompt_scores, competitive_gaps, queries,
--            improvement_runs, page_inventory, query_page_matches,
--            page_citation_scores, action_cards.
--   DROPPED: audit_runs, page_scores (legacy audit pipeline — no longer written
--            or shown), reddit_opportunities (automated Reddit scout scrapped;
--            community-check data now lives in action_cards.reddit_data).
--   FIXES folded in (were latent bugs in the migration chain):
--     * action_cards.run_id now references improvement_runs (was audit_runs).
--     * action_cards.page_url is now nullable (brief/community-check cards
--       legitimately have no page).
--     * pipeline_runs now has admin-only RLS (migration 003 omitted it).
--     * clients.cms_type check now includes 'shopify' (the implementor router
--       supports Shopify; the old check rejected it).
--   DROPPED column: tracker_runs.aggregate_citation_rate (never written by the
--     current tracker; the UI uses per_engine_scores / prompt_scores instead).
--
-- Note on queries: the old migration 007 backfilled clients.target_queries into
-- the queries table. That backfill is intentionally omitted here — on a fresh
-- database there is nothing to migrate, and the app manages the queries table
-- directly via /api/admin/queries. Add each client's queries through the app.
-- ============================================================================

-- ─────────────────────────────────────────────
-- 0. Drop everything (idempotent, cascade)
-- ─────────────────────────────────────────────
drop view if exists public.tracker_results_client cascade;

drop table if exists public.action_cards cascade;
drop table if exists public.page_citation_scores cascade;
drop table if exists public.query_page_matches cascade;
drop table if exists public.page_inventory cascade;
drop table if exists public.improvement_runs cascade;
drop table if exists public.queries cascade;
drop table if exists public.competitive_gaps cascade;
drop table if exists public.prompt_scores cascade;
drop table if exists public.pipeline_runs cascade;
drop table if exists public.reports cascade;
drop table if exists public.tracker_results cascade;
drop table if exists public.tracker_runs cascade;
drop table if exists public.client_users cascade;
drop table if exists public.clients cascade;
-- legacy tables that this version no longer uses
drop table if exists public.reddit_opportunities cascade;
drop table if exists public.page_scores cascade;
drop table if exists public.audit_runs cascade;

drop function if exists public.get_my_client_id() cascade;
drop function if exists public.is_admin() cascade;

-- ─────────────────────────────────────────────
-- 1. Core tables
-- ─────────────────────────────────────────────
create table public.clients (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  brand_name text not null,
  website_domain text default '',
  brand_variations jsonb default '[]'::jsonb,
  target_queries jsonb default '[]'::jsonb,
  competitors jsonb default '[]'::jsonb,
  cms_type text default 'copy_paste'
    check (cms_type in ('github', 'wordpress', 'webflow', 'shopify', 'copy_paste')),
  cms_config jsonb default '{}'::jsonb,
  cycle_frequency text default 'weekly',
  cycle_day integer default 1,
  gsc_site_url text default '',
  auto_approve_action_types text[] default '{}',
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
  non_branded_mention_rate numeric,
  aggregate_avg_mention_level float default 0,
  bucket_scores jsonb default '{}'::jsonb,
  per_engine_scores jsonb default '{}'::jsonb,
  competitor_scores jsonb default '{}'::jsonb,
  discovered_competitors jsonb default '[]'::jsonb,
  gsc_clicks int default 0,
  gsc_impressions int default 0,
  gsc_ctr float default 0,
  gsc_position float default 0,
  gsc_top_queries jsonb default '[]'::jsonb,
  thread_id text
);

create table public.tracker_results (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.tracker_runs(id) on delete cascade,
  query_id uuid,
  query text not null,
  bucket text check (bucket in ('awareness', 'consideration', 'branded')),
  engine text not null,
  model text default '',
  brand_mentioned boolean default false,
  brand_cited boolean default false,
  citation_url text,
  competitor_mentions jsonb default '[]'::jsonb,
  response_text text default '',
  queried_at timestamptz default now(),
  run_number integer,
  mention_level integer default 0,
  mention_level_label text default 'not_mentioned'
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

create table public.pipeline_runs (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  thread_id text not null,
  run_type text not null default 'full',
  status text not null default 'running'
    check (status in ('running', 'awaiting_approval', 'implementing', 'completed', 'error')),
  started_at timestamptz default now(),
  completed_at timestamptz,
  error_message text
);

create table public.prompt_scores (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.tracker_runs(id) on delete cascade,
  client_id uuid not null references public.clients(id) on delete cascade,
  query_id uuid,
  query text not null,
  bucket text check (bucket in ('awareness', 'consideration', 'branded')),
  llm text not null,
  mention_rate numeric default 0,
  avg_mention_level numeric default 0,
  citation_rate numeric default 0,
  created_at timestamptz default now()
);

create table public.competitive_gaps (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.tracker_runs(id) on delete cascade,
  client_id uuid not null references public.clients(id) on delete cascade,
  query_id uuid,
  query text not null,
  bucket text check (bucket in ('awareness', 'consideration', 'branded')),
  client_mention_rate numeric default 0,
  client_avg_mention_level numeric default 0,
  competitor_data jsonb default '[]'::jsonb,
  created_at timestamptz default now()
);

create table public.queries (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  prompt_text text not null,
  slug text not null,
  bucket text not null default 'consideration'
    check (bucket in ('awareness', 'consideration', 'branded')),
  set_type text not null default 'core' check (set_type in ('core', 'discovery')),
  status text not null default 'active' check (status in ('active', 'retired')),
  version integer not null default 1,
  retired_at timestamptz,
  created_at timestamptz default now(),
  unique (client_id, slug)
);

alter table public.tracker_results
  add constraint tracker_results_query_id_fkey
  foreign key (query_id) references public.queries(id) on delete set null;

alter table public.prompt_scores
  add constraint prompt_scores_query_id_fkey
  foreign key (query_id) references public.queries(id) on delete set null;

alter table public.competitive_gaps
  add constraint competitive_gaps_query_id_fkey
  foreign key (query_id) references public.queries(id) on delete set null;

-- ─────────────────────────────────────────────
-- 2. Improvement pipeline tables
-- ─────────────────────────────────────────────
create table public.improvement_runs (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  ran_at timestamptz default now(),
  crawlability_report jsonb default '{}'::jsonb,
  pages_inventoried int default 0,
  queries_matched int default 0,
  content_gaps_found int default 0,
  competitive_gaps_found int default 0,
  cards_generated int default 0,
  status text default 'running' check (status in ('running', 'completed', 'error')),
  error_message text,
  completed_at timestamptz,
  thread_id text
);

create table public.page_inventory (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.improvement_runs(id) on delete cascade,
  url text not null,
  title text default '',
  h1 text default '',
  first_paragraph text default '',
  schema_types text[] default '{}',
  word_count int default 0,
  last_modified timestamptz,
  outbound_link_count int default 0,
  has_faq_schema boolean default false,
  has_comparison_table boolean default false
);

create table public.query_page_matches (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.improvement_runs(id) on delete cascade,
  query_id uuid not null references public.queries(id) on delete cascade,
  query_text text not null,
  match_type text not null check (match_type in ('matched', 'weak', 'content_gap')),
  matched_page_url text,
  similarity_score float default 0,
  bucket text
);

create table public.page_citation_scores (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.improvement_runs(id) on delete cascade,
  page_url text not null,
  structural_score int default 0,
  check_results jsonb default '{}'::jsonb,
  sonnet_quality jsonb default '{}'::jsonb,
  schema_status text default 'missing'
    check (schema_status in ('missing', 'broken', 'valid_incomplete', 'valid_complete')),
  schema_errors text[] default '{}'
);

-- action_cards: run_id now references improvement_runs; page_url nullable.
-- pillar/score are legacy columns still written by the pipeline; the new UI
-- reads action_type / structural_score instead.
create table public.action_cards (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.improvement_runs(id) on delete cascade,
  client_id uuid references public.clients(id),
  query_id uuid references public.queries(id),
  page_url text,
  pillar text not null default 'general',
  score int not null default 0,
  action_type text default 'general',
  track text default 'automated' check (track in ('automated', 'manual')),
  priority int default 3,
  competitive_gap float,
  structural_score int,
  validation_passed boolean default true,
  issue text default '',
  before_text text default '',
  after_text text default '',
  code_block text default '',
  brief jsonb,
  reddit_data jsonb,
  preview_url text,
  auto_approved boolean default false,
  verification jsonb,
  status text default 'pending'
    check (status in ('pending', 'approved', 'rejected', 'implemented')),
  cms_action text default 'copy_paste'
    check (cms_action in ('none', 'github_pr', 'wordpress_api', 'webflow_staging', 'copy_paste')),
  created_at timestamptz default now()
);

-- ─────────────────────────────────────────────
-- 3. Client-facing view (tracker_results without response_text)
-- ─────────────────────────────────────────────
create view public.tracker_results_client as
select
  id, run_id, query, engine, model,
  brand_mentioned, brand_cited, citation_url,
  competitor_mentions, queried_at,
  run_number, mention_level, mention_level_label
from public.tracker_results;

-- ─────────────────────────────────────────────
-- 4. Helper functions
-- ─────────────────────────────────────────────
create or replace function public.get_my_client_id()
returns uuid language sql stable security definer as $$
  select client_id from public.client_users where user_id = auth.uid() limit 1;
$$;

create or replace function public.is_admin()
returns boolean language sql stable security definer as $$
  select exists (
    select 1 from public.client_users
    where user_id = auth.uid() and role = 'admin'
  );
$$;

-- ─────────────────────────────────────────────
-- 5. Indexes
-- ─────────────────────────────────────────────
create index idx_client_users_user_id on public.client_users(user_id);
create index idx_client_users_client_id on public.client_users(client_id);
create index idx_tracker_runs_client_id on public.tracker_runs(client_id);
create index idx_tracker_runs_thread_id on public.tracker_runs(thread_id);
create index idx_tracker_results_run_id on public.tracker_results(run_id);
create index idx_tracker_results_query_id on public.tracker_results(query_id);
create index idx_tracker_results_bucket on public.tracker_results(bucket);
create index idx_reports_client_id on public.reports(client_id);
create index idx_reports_status on public.reports(status);
create index idx_pipeline_runs_client on public.pipeline_runs(client_id);
create index idx_pipeline_runs_status on public.pipeline_runs(status);
create index idx_prompt_scores_run_id on public.prompt_scores(run_id);
create index idx_prompt_scores_client_id on public.prompt_scores(client_id);
create index idx_prompt_scores_query_id on public.prompt_scores(query_id);
create index idx_prompt_scores_bucket on public.prompt_scores(bucket);
create index idx_competitive_gaps_run_id on public.competitive_gaps(run_id);
create index idx_competitive_gaps_client_id on public.competitive_gaps(client_id);
create index idx_competitive_gaps_query_id on public.competitive_gaps(query_id);
create index idx_competitive_gaps_bucket on public.competitive_gaps(bucket);
create index idx_queries_client_id on public.queries(client_id);
create index idx_queries_status on public.queries(status);
create index idx_improvement_runs_client_id on public.improvement_runs(client_id);
create index idx_improvement_runs_thread_id on public.improvement_runs(thread_id);
create index idx_page_inventory_run_id on public.page_inventory(run_id);
create index idx_query_page_matches_run_id on public.query_page_matches(run_id);
create index idx_query_page_matches_query_id on public.query_page_matches(query_id);
create index idx_page_citation_scores_run_id on public.page_citation_scores(run_id);
create index idx_action_cards_run_id on public.action_cards(run_id);
create index idx_action_cards_client_id on public.action_cards(client_id);
create index idx_action_cards_query_id on public.action_cards(query_id);
create index idx_action_cards_status on public.action_cards(status);
create index idx_action_cards_track on public.action_cards(track);
create index idx_action_cards_auto_approved on public.action_cards(auto_approved) where auto_approved = true;

-- ─────────────────────────────────────────────
-- 6. Row Level Security
-- ─────────────────────────────────────────────
alter table public.clients enable row level security;
alter table public.client_users enable row level security;
alter table public.tracker_runs enable row level security;
alter table public.tracker_results enable row level security;
alter table public.reports enable row level security;
alter table public.pipeline_runs enable row level security;
alter table public.prompt_scores enable row level security;
alter table public.competitive_gaps enable row level security;
alter table public.queries enable row level security;
alter table public.improvement_runs enable row level security;
alter table public.page_inventory enable row level security;
alter table public.query_page_matches enable row level security;
alter table public.page_citation_scores enable row level security;
alter table public.action_cards enable row level security;

-- clients
create policy "Admins manage clients" on public.clients
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Clients view own client" on public.clients
  for select using (id = public.get_my_client_id());

-- client_users
create policy "Admins manage client_users" on public.client_users
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Users view own client_users row" on public.client_users
  for select using (user_id = auth.uid());

-- tracker_runs
create policy "Admins manage tracker_runs" on public.tracker_runs
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Clients view own tracker_runs" on public.tracker_runs
  for select using (client_id = public.get_my_client_id());

-- tracker_results (admins only; clients use the view)
create policy "Admins manage tracker_results" on public.tracker_results
  for all using (public.is_admin()) with check (public.is_admin());

-- reports
create policy "Admins manage reports" on public.reports
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Clients view own published reports" on public.reports
  for select using (status = 'published' and client_id = public.get_my_client_id());

-- pipeline_runs (admin only)
create policy "Admins manage pipeline_runs" on public.pipeline_runs
  for all using (public.is_admin()) with check (public.is_admin());

-- prompt_scores
create policy "Admins manage prompt_scores" on public.prompt_scores
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Clients view own prompt_scores" on public.prompt_scores
  for select using (client_id = public.get_my_client_id());

-- competitive_gaps
create policy "Admins manage competitive_gaps" on public.competitive_gaps
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Clients view own competitive_gaps" on public.competitive_gaps
  for select using (client_id = public.get_my_client_id());

-- queries
create policy "Admins manage queries" on public.queries
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Clients view own queries" on public.queries
  for select using (client_id = public.get_my_client_id());

-- improvement pipeline tables (admin only)
create policy "Admins manage improvement_runs" on public.improvement_runs
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Admins manage page_inventory" on public.page_inventory
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Admins manage query_page_matches" on public.query_page_matches
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Admins manage page_citation_scores" on public.page_citation_scores
  for all using (public.is_admin()) with check (public.is_admin());
create policy "Admins manage action_cards" on public.action_cards
  for all using (public.is_admin()) with check (public.is_admin());

-- ─────────────────────────────────────────────
-- 7. Grants
-- ─────────────────────────────────────────────
grant select on public.tracker_results_client to authenticated;
