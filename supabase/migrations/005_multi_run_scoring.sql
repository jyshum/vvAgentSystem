-- 005_multi_run_scoring.sql
-- Phase 1: Multi-run execution + new scoring model

-- ══════════════════════════════════════════════
-- 1. Add columns to tracker_results
-- ══════════════════════════════════════════════

alter table public.tracker_results
  add column run_number integer,
  add column mention_level integer default 0,
  add column mention_level_label text default 'not_mentioned';

-- ══════════════════════════════════════════════
-- 2. Add avg mention level to tracker_runs
-- ══════════════════════════════════════════════

alter table public.tracker_runs
  add column aggregate_avg_mention_level float default 0;

-- Keep aggregate_citation_rate column for now (old rows use it),
-- but new code will not write to it.

-- ══════════════════════════════════════════════
-- 3. Create prompt_scores table
-- ══════════════════════════════════════════════

create table public.prompt_scores (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.tracker_runs(id) on delete cascade,
  client_id uuid not null references public.clients(id) on delete cascade,
  query text not null,
  llm text not null,
  mention_rate numeric default 0,
  avg_mention_level numeric default 0,
  citation_rate numeric default 0,
  created_at timestamptz default now()
);

create index idx_prompt_scores_run_id on public.prompt_scores(run_id);
create index idx_prompt_scores_client_id on public.prompt_scores(client_id);

-- RLS
alter table public.prompt_scores enable row level security;

create policy "Admins can manage prompt_scores"
  on public.prompt_scores for all
  using (public.is_admin())
  with check (public.is_admin());

create policy "Clients can view their own prompt_scores"
  on public.prompt_scores for select
  using (client_id = public.get_my_client_id());

-- ══════════════════════════════════════════════
-- 4. Update client view to include new columns
-- ══════════════════════════════════════════════

drop view if exists public.tracker_results_client;

create view public.tracker_results_client as
select
  id, run_id, query, engine, model,
  brand_mentioned, brand_cited, citation_url,
  competitor_mentions, queried_at,
  run_number, mention_level, mention_level_label
from public.tracker_results;

grant select on public.tracker_results_client to authenticated;
