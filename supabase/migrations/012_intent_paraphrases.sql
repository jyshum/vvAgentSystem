-- 012_intent_paraphrases.sql
-- Intent-based tracking: each queries row is an intent carrying its paraphrases;
-- tracker_runs records a signature of the active intent set so trend breaks show.

alter table public.queries
  add column if not exists paraphrases jsonb default '[]'::jsonb;

alter table public.tracker_runs
  add column if not exists query_set_signature text,
  add column if not exists query_set_changed boolean default false;
