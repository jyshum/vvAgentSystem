export interface Client {
  id: string;
  name: string;
  brand_name: string;
  website_domain: string;
  brand_variations: string[];
  target_queries: string[];
  competitors: string[];
  cms_type: string;
  cms_config: Record<string, string>;
  gsc_site_url: string;
  cycle_frequency: string;
  cycle_day: number;
  created_at: string;
}

export interface ClientUser {
  id: string;
  user_id: string;
  client_id: string | null;
  role: "admin" | "client";
  created_at: string;
}

export interface TrackerRun {
  id: string;
  client_id: string;
  ran_at: string;
  aggregate_mention_rate: number;
  aggregate_avg_mention_level: number;
  per_engine_scores: Record<
    string,
    { mention_rate: number; avg_mention_level: number; citation_rate: number }
  >;
  competitor_scores: Record<string, { mention_rate: number }>;
  gsc_clicks: number;
  gsc_impressions: number;
  gsc_ctr: number;
  gsc_position: number;
  gsc_top_queries: { query: string; clicks: number; impressions: number; ctr: number; position: number }[];
}

export interface TrackerResult {
  id: string;
  run_id: string;
  query: string;
  engine: string;
  model: string;
  brand_mentioned: boolean;
  brand_cited: boolean;
  citation_url: string | null;
  competitor_mentions: string[];
  response_text: string;
  queried_at: string;
  run_number: number;
  mention_level: number;
  mention_level_label: string;
}

export interface TrackerResultClient {
  id: string;
  run_id: string;
  query: string;
  engine: string;
  model: string;
  brand_mentioned: boolean;
  brand_cited: boolean;
  citation_url: string | null;
  competitor_mentions: string[];
  response_text?: string;
  queried_at: string;
  run_number: number;
  mention_level: number;
  mention_level_label: string;
}

export interface PromptScore {
  id: string;
  run_id: string;
  client_id: string;
  query: string;
  llm: string;
  mention_rate: number;
  avg_mention_level: number;
  citation_rate: number;
  created_at: string;
}

export interface Report {
  id: string;
  client_id: string;
  run_id: string | null;
  week_start: string;
  status: "draft" | "published";
  exec_summary: string;
  work_completed: { text: string; done: boolean }[];
  priorities: { text: string }[];
  highlights: { text: string }[];
  blockers: { text: string }[];
  notes: string;
  search_console: SearchConsoleMetrics | null;
  published_at: string | null;
  created_at: string;
}

export interface SearchConsoleMetrics {
  impressions: { week: number | null; baseline: number | null };
  clicks: { week: number | null; baseline: number | null };
  ctr: { week: number | null; baseline: number | null };
  position: { week: number | null; baseline: number | null };
}

export interface ReportWithRun extends Report {
  tracker_run: TrackerRun | null;
}
