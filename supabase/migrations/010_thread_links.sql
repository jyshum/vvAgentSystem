-- 010_thread_links.sql
-- Link tracker_runs and improvement_runs to their pipeline_runs thread so the
-- approvals inbox can resume the correct thread and run detail can join all
-- three tables. Old rows keep null thread_id; UI joins must tolerate that.

alter table public.tracker_runs
  add column if not exists thread_id text;

alter table public.improvement_runs
  add column if not exists thread_id text;

create index if not exists idx_tracker_runs_thread_id
  on public.tracker_runs(thread_id);

create index if not exists idx_improvement_runs_thread_id
  on public.improvement_runs(thread_id);
