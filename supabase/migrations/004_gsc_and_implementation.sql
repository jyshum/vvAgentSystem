-- GSC site URL on clients
alter table public.clients
  add column if not exists gsc_site_url text default '';

-- GSC metrics on tracker_runs
alter table public.tracker_runs
  add column if not exists gsc_clicks int default 0,
  add column if not exists gsc_impressions int default 0,
  add column if not exists gsc_ctr float default 0,
  add column if not exists gsc_position float default 0,
  add column if not exists gsc_top_queries jsonb default '[]'::jsonb;
