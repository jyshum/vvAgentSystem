export interface PipelineRun {
  id: string;
  client_id: string;
  thread_id: string;
  run_type: string;
  status: "running" | "awaiting_approval" | "implementing" | "completed" | "error";
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface CrawlCheck { status: "pass" | "fail" | "warn" | string; detail?: string }

export interface CrawlabilityReport {
  has_critical_blocker?: boolean;
  robots_txt?: CrawlCheck;
  js_rendering?: CrawlCheck;
  cdn_blocks?: CrawlCheck;
  [key: string]: unknown;
}

export type ImprovementRunMode = "legacy" | "technical_v1";
export type TechnicalAuditCheckSet = "foundation";

export interface ImprovementRun {
  id: string;
  client_id: string;
  thread_id: string | null;
  run_mode: ImprovementRunMode;
  effective_check_sets: TechnicalAuditCheckSet[];
  ran_at: string;
  crawlability_report: CrawlabilityReport;
  pages_inventoried: number;
  queries_matched: number;
  content_gaps_found: number;
  competitive_gaps_found: number;
  cards_generated: number;
  status: "running" | "completed" | "error";
  error_message: string | null;
  completed_at: string | null;
}

export interface PageInventoryRow {
  id: string;
  run_id: string;
  url: string;
  title: string;
  h1: string;
  first_paragraph: string;
  schema_types: string[];
  word_count: number;
  last_modified: string | null;
  outbound_link_count: number;
  has_faq_schema: boolean;
  has_comparison_table: boolean;
}

export interface QueryPageMatch {
  id: string;
  run_id: string;
  query_id: string;
  query_text: string;
  match_type: "matched" | "weak" | "content_gap";
  matched_page_url: string | null;
  similarity_score: number;
  bucket: string | null;
}

export interface CheckResult { score: number; detail?: string; [key: string]: unknown }

export interface SonnetQuality {
  specificity: number;
  completeness: number;
  answer_directness: number;
  summary: string;
}

export interface PageCitationScore {
  id: string;
  run_id: string;
  page_url: string;
  structural_score: number;
  check_results: Record<string, CheckResult>;
  sonnet_quality: SonnetQuality;
  schema_status: "missing" | "broken" | "valid_incomplete" | "valid_complete";
  schema_errors: string[];
}

export interface ActionCard {
  id: string;
  run_id: string;
  client_id: string | null;
  query_id: string | null;
  page_url: string | null;
  action_type: string;
  /** Legacy-named base columns (migration 002), set on every card. The new UI
   * displays action_type/structural_score instead of reading these. */
  pillar: string;
  score: number;
  track: "automated" | "manual";
  priority: number;
  competitive_gap: number | null;
  structural_score: number | null;
  issue: string;
  before_text: string;
  after_text: string;
  code_block: string;
  status: "pending" | "approved" | "rejected" | "implemented";
  cms_action: string;
  auto_approved: boolean;
  validation_passed: boolean;
  verification: { verified: boolean; checks?: Record<string, unknown>; error?: string } | null;
  brief: {
    target_query: string;
    competitive_landscape: string;
    recommended_title: string;
    recommended_h1: string;
    key_sections: string[];
    facts_to_include: string[];
    schema_type: string;
    internal_link_targets: string[];
    word_count_target: number;
  } | null;
  reddit_data: {
    search_links?: { reddit: string; google: string };
    guidance?: string;
    thread_url?: string | null;
  } | null;
  preview_url: string | null;
  created_at: string;
}
