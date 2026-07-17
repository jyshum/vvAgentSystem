-- Per-stage progress for a running pipeline. The background job writes a human
-- label ("Querying AI engines", "Fetching Search Console", "Running technical
-- audit") as each node starts, so the dashboard can show live progress instead
-- of a single opaque "running" state. Nullable and additive; older rows and
-- completed runs simply have no stage.
alter table public.pipeline_runs
  add column if not exists stage text;
