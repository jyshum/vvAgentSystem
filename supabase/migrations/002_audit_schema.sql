-- ══════════════════════════════════════════════
-- Audit tables
-- ══════════════════════════════════════════════

alter table public.clients
  add column if not exists cms_type text default 'copy_paste'
    check (cms_type in ('github', 'wordpress', 'webflow', 'copy_paste')),
  add column if not exists cms_config jsonb default '{}'::jsonb;

create table public.audit_runs (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  ran_at timestamptz default now(),
  pages_audited int default 0,
  site_score int default 0,
  pillar_averages jsonb default '{}'::jsonb,
  weakest_pillar text default ''
);

create table public.page_scores (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.audit_runs(id) on delete cascade,
  url text not null,
  title text default '',
  word_count int default 0,
  total_score int default 0,
  pillar_scores jsonb default '{}'::jsonb
);

create table public.action_cards (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.audit_runs(id) on delete cascade,
  page_url text not null,
  pillar text not null,
  score int not null,
  issue text default '',
  before_text text default '',
  after_text text default '',
  code_block text default '',
  status text default 'pending'
    check (status in ('pending', 'approved', 'rejected', 'implemented')),
  cms_action text default 'copy_paste'
    check (cms_action in ('none', 'github_pr', 'wordpress_api', 'copy_paste')),
  created_at timestamptz default now()
);

create table public.reddit_opportunities (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  title text not null,
  url text not null,
  subreddit text default '',
  score int default 0,
  num_comments int default 0,
  relevance_score float default 0,
  selftext_preview text default '',
  status text default 'new' check (status in ('new', 'posted', 'skipped')),
  found_at timestamptz default now()
);

-- Indexes
create index idx_audit_runs_client_id on public.audit_runs(client_id);
create index idx_page_scores_run_id on public.page_scores(run_id);
create index idx_action_cards_run_id on public.action_cards(run_id);
create index idx_action_cards_status on public.action_cards(status);
create index idx_reddit_opportunities_client_id on public.reddit_opportunities(client_id);

-- RLS
alter table public.audit_runs enable row level security;
alter table public.page_scores enable row level security;
alter table public.action_cards enable row level security;
alter table public.reddit_opportunities enable row level security;

create policy "Admins can manage audit_runs"
  on public.audit_runs for all
  using (public.is_admin()) with check (public.is_admin());

create policy "Admins can manage page_scores"
  on public.page_scores for all
  using (public.is_admin()) with check (public.is_admin());

create policy "Admins can manage action_cards"
  on public.action_cards for all
  using (public.is_admin()) with check (public.is_admin());

create policy "Admins can manage reddit_opportunities"
  on public.reddit_opportunities for all
  using (public.is_admin()) with check (public.is_admin());
