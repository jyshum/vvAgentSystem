-- 007_queries.sql
-- Phase 4: Query management

-- ══════════════════════════════════════════════
-- 1. Create queries table
-- ══════════════════════════════════════════════

create table public.queries (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  prompt_text text not null,
  slug text not null,
  bucket text not null default 'consideration' check (bucket in ('awareness', 'consideration', 'branded')),
  set_type text not null default 'core' check (set_type in ('core', 'discovery')),
  status text not null default 'active' check (status in ('active', 'retired')),
  version integer not null default 1,
  retired_at timestamptz,
  created_at timestamptz default now(),
  unique(client_id, slug)
);

create index idx_queries_client_id on public.queries(client_id);
create index idx_queries_status on public.queries(status);

-- RLS
alter table public.queries enable row level security;

create policy "Admins can manage queries"
  on public.queries for all
  using (public.is_admin())
  with check (public.is_admin());

create policy "Clients can view their own queries"
  on public.queries for select
  using (client_id = public.get_my_client_id());

-- ══════════════════════════════════════════════
-- 2. Migrate existing target_queries into queries table
-- ══════════════════════════════════════════════

-- For each client, insert their target_queries as active core consideration queries.
-- Slug is generated from prompt text: lowercase, non-alphanum → underscore, truncate 60, append _v1.
-- Uses ON CONFLICT to be idempotent.

insert into public.queries (client_id, prompt_text, slug, bucket, set_type, status, version)
select
  c.id as client_id,
  q.value::text as prompt_text,
  left(
    regexp_replace(lower(trim(both '"' from q.value::text)), '[^a-z0-9]+', '_', 'g'),
    60
  ) || '_v1' as slug,
  'consideration' as bucket,
  'core' as set_type,
  'active' as status,
  1 as version
from public.clients c,
     jsonb_array_elements(c.target_queries) as q
where jsonb_array_length(c.target_queries) > 0
on conflict (client_id, slug) do nothing;
