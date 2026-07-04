-- 006_competitive_gaps.sql
-- Phase 2: Competitive gap matrix

-- ══════════════════════════════════════════════
-- 1. Create competitive_gaps table
-- ══════════════════════════════════════════════

create table public.competitive_gaps (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.tracker_runs(id) on delete cascade,
  client_id uuid not null references public.clients(id) on delete cascade,
  query text not null,
  client_mention_rate numeric default 0,
  client_avg_mention_level numeric default 0,
  competitor_data jsonb default '[]',
  created_at timestamptz default now()
);

create index idx_competitive_gaps_run_id on public.competitive_gaps(run_id);
create index idx_competitive_gaps_client_id on public.competitive_gaps(client_id);

-- RLS
alter table public.competitive_gaps enable row level security;

create policy "Admins can manage competitive_gaps"
  on public.competitive_gaps for all
  using (public.is_admin())
  with check (public.is_admin());

create policy "Clients can view their own competitive_gaps"
  on public.competitive_gaps for select
  using (client_id = public.get_my_client_id());

-- ══════════════════════════════════════════════
-- 2. Add discovered_competitors to tracker_runs
-- ══════════════════════════════════════════════

alter table public.tracker_runs
  add column discovered_competitors jsonb default '[]';
