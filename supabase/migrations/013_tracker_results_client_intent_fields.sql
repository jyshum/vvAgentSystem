-- 013_tracker_results_client_intent_fields.sql
-- Expose intent identity to client-facing reports without exposing response_text.

drop view if exists public.tracker_results_client;

create view public.tracker_results_client as
select
  id,
  run_id,
  query_id,
  query,
  bucket,
  engine,
  model,
  brand_mentioned,
  brand_cited,
  citation_url,
  competitor_mentions,
  queried_at,
  run_number,
  mention_level,
  mention_level_label
from public.tracker_results;

grant select on public.tracker_results_client to authenticated;
