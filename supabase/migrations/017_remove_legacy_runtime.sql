drop table if exists public.action_cards cascade;
drop table if exists public.page_citation_scores cascade;
drop table if exists public.query_page_matches cascade;
drop table if exists public.page_inventory cascade;
drop table if exists public.client_site_profiles cascade;

drop trigger if exists improvement_runs_route_controls_immutable on public.improvement_runs;
drop function if exists public.prevent_improvement_run_route_mutation();

alter table public.clients
  drop column if exists cycle_frequency,
  drop column if exists cycle_day,
  drop column if exists cms_type,
  drop column if exists cms_config,
  drop column if exists auto_approve_action_types;

alter table public.improvement_runs
  drop column if exists crawlability_report,
  drop column if exists pages_inventoried,
  drop column if exists queries_matched,
  drop column if exists content_gaps_found,
  drop column if exists cards_generated,
  drop column if exists run_mode,
  drop column if exists effective_check_sets;

alter table public.pipeline_runs drop constraint if exists pipeline_runs_status_check;
alter table public.pipeline_runs
  add constraint pipeline_runs_status_check
  check (status in ('running', 'completed', 'error'));
