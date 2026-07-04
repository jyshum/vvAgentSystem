-- 008_improvement_pipeline.sql
-- AI Visibility Improvement Pipeline schema

-- ══════════════════════════════════════════════
-- 1. improvement_runs table
-- ══════════════════════════════════════════════

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
  completed_at timestamptz
);

-- ══════════════════════════════════════════════
-- 2. page_inventory table
-- ══════════════════════════════════════════════

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

-- ══════════════════════════════════════════════
-- 3. query_page_matches table
-- ══════════════════════════════════════════════

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

-- ══════════════════════════════════════════════
-- 4. page_citation_scores table
-- ══════════════════════════════════════════════

create table public.page_citation_scores (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.improvement_runs(id) on delete cascade,
  page_url text not null,
  structural_score int default 0,
  check_results jsonb default '{}'::jsonb,
  sonnet_quality jsonb default '{}'::jsonb,
  schema_status text default 'missing' check (schema_status in ('missing', 'broken', 'valid_incomplete', 'valid_complete')),
  schema_errors text[] default '{}'
);

-- ══════════════════════════════════════════════
-- 5. ALTER action_cards — add new columns
-- ══════════════════════════════════════════════

alter table public.action_cards
  add column if not exists client_id uuid references public.clients(id),
  add column if not exists query_id uuid references public.queries(id),
  add column if not exists action_type text default 'general',
  add column if not exists track text default 'automated' check (track in ('automated', 'manual')),
  add column if not exists priority int default 3,
  add column if not exists competitive_gap float,
  add column if not exists structural_score int,
  add column if not exists validation_passed boolean default true,
  add column if not exists brief jsonb,
  add column if not exists preview_url text,
  add column if not exists reddit_data jsonb;

-- ══════════════════════════════════════════════
-- 6. Update cms_action constraint to include 'webflow_staging'
-- ══════════════════════════════════════════════

alter table public.action_cards
  drop constraint if exists action_cards_cms_action_check;

alter table public.action_cards
  add constraint action_cards_cms_action_check
  check (cms_action in ('none', 'github_pr', 'wordpress_api', 'webflow_staging', 'copy_paste'));

-- ══════════════════════════════════════════════
-- 7. Indexes
-- ══════════════════════════════════════════════

create index idx_improvement_runs_client_id on public.improvement_runs(client_id);
create index idx_page_inventory_run_id on public.page_inventory(run_id);
create index idx_query_page_matches_run_id on public.query_page_matches(run_id);
create index idx_query_page_matches_query_id on public.query_page_matches(query_id);
create index idx_page_citation_scores_run_id on public.page_citation_scores(run_id);
create index idx_action_cards_client_id on public.action_cards(client_id);
create index idx_action_cards_query_id on public.action_cards(query_id);
create index idx_action_cards_track on public.action_cards(track);

-- ══════════════════════════════════════════════
-- 8. RLS policies (admin-only)
-- ══════════════════════════════════════════════

alter table public.improvement_runs enable row level security;

create policy "Admins can manage improvement_runs"
  on public.improvement_runs for all
  using (public.is_admin())
  with check (public.is_admin());

alter table public.page_inventory enable row level security;

create policy "Admins can manage page_inventory"
  on public.page_inventory for all
  using (public.is_admin())
  with check (public.is_admin());

alter table public.query_page_matches enable row level security;

create policy "Admins can manage query_page_matches"
  on public.query_page_matches for all
  using (public.is_admin())
  with check (public.is_admin());

alter table public.page_citation_scores enable row level security;

create policy "Admins can manage page_citation_scores"
  on public.page_citation_scores for all
  using (public.is_admin())
  with check (public.is_admin());
