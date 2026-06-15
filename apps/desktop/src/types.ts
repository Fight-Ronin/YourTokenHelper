export type SourceKind =
  | "codex"
  | "claude_code"
  | "cursor"
  | "gemini_cli"
  | "github_copilot"
  | "openai_api_cost"
  | "claude_api_cost"
  | "gemini_api_cost"
  | "deepseek_api_cost";

export type ApiCostSourceKind =
  | "openai_api_cost"
  | "claude_api_cost"
  | "gemini_api_cost"
  | "deepseek_api_cost";

export type SourceStatus =
  | "ready"
  | "not_found"
  | "permission_denied"
  | "setup_required"
  | "official_report"
  | "manual_only"
  | "secondary_source"
  | "error";

export type SourceConfidence =
  | "official"
  | "local_exact"
  | "local_estimated"
  | "manual"
  | "unavailable";

export type TokenTotals = {
  input_tokens: number;
  output_tokens: number;
  cached_input_tokens: number;
  reasoning_output_tokens: number;
  total_tokens: number;
};

export type CostSourceTotals = {
  total_usd: number;
  bucket_count: number;
  event_count: number;
};

export type CostSummary = {
  window_start: string | null;
  window_end: string | null;
  total_usd: number | null;
  by_source: Partial<Record<ApiCostSourceKind, CostSourceTotals>>;
};

export type UsageSummary = {
  event_count: number;
  totals: TokenTotals;
  by_source: Record<SourceKind, TokenTotals>;
  by_day: Record<string, TokenTotals>;
  by_day_source: Record<string, Record<SourceKind, TokenTotals>>;
  rolling_7d: {
    window_start: string | null;
    window_end: string | null;
    totals: TokenTotals;
  };
};

export type AllowanceWindow = {
  source_kind: SourceKind;
  source_id: string;
  status: "api_backed" | "manual" | "derived" | "unavailable";
  unit: "tokens" | "credits" | "usd" | "requests" | "unknown";
  window_start?: string;
  window_end?: string;
  reset_at?: string;
  limit_amount?: number;
  used_amount?: number;
  remaining_amount?: number;
  note?: string;
};

export type SourceState = {
  source_kind: SourceKind;
  status: SourceStatus;
  confidence: SourceConfidence;
};

export type RefreshState = {
  last_attempt_at: string | null;
  last_success_at: string | null;
  last_status: "never_refreshed" | "mock" | "blocked" | "failed" | "partial" | "succeeded";
  successful_source_count: number;
  attempted_source_count: number;
  events_seen: number;
};

export type MockSummaryPayload = {
  schema_version: number;
  generated_from: string;
  privacy: {
    synthetic: boolean;
    stores_prompt_content: boolean;
    stores_response_content: boolean;
    stores_tool_output: boolean;
  };
  refresh_state: RefreshState;
  summary: UsageSummary;
  cost_summary: CostSummary;
  allowance_windows: AllowanceWindow[];
  source_states: SourceState[];
};

export type RefreshResult = {
  source_kind: Exclude<SourceKind, ApiCostSourceKind>;
  source_id: string;
  status: SourceStatus;
  confidence: SourceConfidence;
  events_seen: number;
  sync_run_id: number;
  message?: string;
};

export type RefreshUsageSummary = Omit<UsageSummary, "by_source" | "by_day_source"> & {
  by_source: Partial<Record<SourceKind, TokenTotals>>;
  by_day_source?: Record<string, Partial<Record<SourceKind, TokenTotals>>>;
};

export type RefreshStorageSummaryPayload = Omit<MockSummaryPayload, "summary"> & {
  summary: RefreshUsageSummary;
};

export type SourceRefreshSummaryPayload = {
  refresh_results: RefreshResult[];
  storage_summary: RefreshStorageSummaryPayload;
};
