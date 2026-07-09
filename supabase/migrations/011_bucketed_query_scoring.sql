-- 011_bucketed_query_scoring.sql
-- Carry query bucket metadata into tracker outputs and separate branded prompts
-- from the primary non-branded visibility score.

alter table public.tracker_runs
  add column if not exists non_branded_mention_rate numeric,
  add column if not exists bucket_scores jsonb default '{}'::jsonb;

alter table public.tracker_results
  add column if not exists query_id uuid references public.queries(id) on delete set null,
  add column if not exists bucket text check (bucket in ('awareness', 'consideration', 'branded'));

alter table public.prompt_scores
  add column if not exists query_id uuid references public.queries(id) on delete set null,
  add column if not exists bucket text check (bucket in ('awareness', 'consideration', 'branded'));

alter table public.competitive_gaps
  add column if not exists query_id uuid references public.queries(id) on delete set null,
  add column if not exists bucket text check (bucket in ('awareness', 'consideration', 'branded'));

create index if not exists idx_tracker_results_query_id on public.tracker_results(query_id);
create index if not exists idx_tracker_results_bucket on public.tracker_results(bucket);
create index if not exists idx_prompt_scores_query_id on public.prompt_scores(query_id);
create index if not exists idx_prompt_scores_bucket on public.prompt_scores(bucket);
create index if not exists idx_competitive_gaps_query_id on public.competitive_gaps(query_id);
create index if not exists idx_competitive_gaps_bucket on public.competitive_gaps(bucket);
