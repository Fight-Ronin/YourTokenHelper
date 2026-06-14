import type {
  MockSummaryPayload,
  RefreshStorageSummaryPayload,
  SourceKind,
  SourceState,
  TokenTotals
} from "../types.js";

const dashboardSourceKinds: SourceKind[] = [
  "codex",
  "claude_code",
  "cursor",
  "gemini_cli",
  "github_copilot",
  "openai_api_cost",
  "claude_api_cost",
  "gemini_api_cost",
  "deepseek_api_cost"
];

const apiCostSourceKinds = new Set<SourceKind>([
  "openai_api_cost",
  "claude_api_cost",
  "gemini_api_cost",
  "deepseek_api_cost"
]);

export type SourceUsageRow = {
  sourceKind: SourceKind;
  totals: TokenTotals;
};

export type DashboardDataMode = "mock" | "local_refresh";
export type StartupStorageReadState =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "loaded" }
  | { phase: "unavailable"; message: string };

export function buildDashboardSummaryFromRefresh(
  storageSummary: RefreshStorageSummaryPayload
): MockSummaryPayload {
  return {
    ...storageSummary,
    summary: {
      ...storageSummary.summary,
      by_source: completeSourceTotals(storageSummary.summary.by_source),
      by_day_source: completeDailySourceTotals(storageSummary.summary.by_day_source ?? {})
    },
    source_states: completeSourceStates(storageSummary.source_states)
  };
}

export function emptyTokenTotals(): TokenTotals {
  return {
    input_tokens: 0,
    output_tokens: 0,
    cached_input_tokens: 0,
    reasoning_output_tokens: 0,
    total_tokens: 0
  };
}

export function latestSummaryDay(payload: MockSummaryPayload) {
  return Object.keys(payload.summary.by_day).sort().at(-1) ?? null;
}

export function sourceTotalsForDay(payload: MockSummaryPayload, day: string): Record<SourceKind, TokenTotals> {
  return completeSourceTotals(payload.summary.by_day_source?.[day] ?? {});
}

export function sourceUsageRows(
  totals: Record<SourceKind, TokenTotals>,
  configuredSourceKinds: readonly SourceKind[] = []
): SourceUsageRow[] {
  const configuredKinds = new Set(configuredSourceKinds);

  return Object.entries(totals)
    .filter(([sourceKind, tokenTotals]) => tokenTotals.total_tokens > 0 || configuredKinds.has(sourceKind as SourceKind))
    .sort(([leftKind, leftTotals], [rightKind, rightTotals]) => {
      const leftIsConfigured = configuredKinds.has(leftKind as SourceKind);
      const rightIsConfigured = configuredKinds.has(rightKind as SourceKind);
      if (leftIsConfigured !== rightIsConfigured) {
        return leftIsConfigured ? -1 : 1;
      }

      const tokenDifference = rightTotals.total_tokens - leftTotals.total_tokens;
      if (tokenDifference !== 0) {
        return tokenDifference;
      }

      return sourceOrder(leftKind as SourceKind) - sourceOrder(rightKind as SourceKind);
    })
    .map(([sourceKind, tokenTotals]) => ({
      sourceKind: sourceKind as SourceKind,
      totals: tokenTotals
    }));
}

export function dashboardQualityLabel(dataMode: DashboardDataMode, startupState: StartupStorageReadState) {
  if (dataMode === "local_refresh") {
    return "Live local aggregate";
  }
  if (startupState.phase === "loading") {
    return "Loading saved aggregate";
  }
  return "Mock data";
}

export function startupStorageStatusLabel(state: StartupStorageReadState) {
  if (state.phase === "loading") {
    return "Checking";
  }
  if (state.phase === "loaded") {
    return "Loaded";
  }
  if (state.phase === "unavailable") {
    return "Unavailable";
  }
  return "Idle";
}

function completeSourceTotals(
  bySource: Partial<Record<SourceKind, TokenTotals>>
): Record<SourceKind, TokenTotals> {
  return Object.fromEntries(
    dashboardSourceKinds.map((sourceKind) => {
      const totals = bySource[sourceKind];
      return [sourceKind, totals ? { ...totals } : emptyTokenTotals()];
    })
  ) as Record<SourceKind, TokenTotals>;
}

function completeDailySourceTotals(
  byDaySource: Record<string, Partial<Record<SourceKind, TokenTotals>>>
): Record<string, Record<SourceKind, TokenTotals>> {
  return Object.fromEntries(
    Object.entries(byDaySource).map(([day, bySource]) => [day, completeSourceTotals(bySource)])
  );
}

function completeSourceStates(sourceStates: SourceState[]): SourceState[] {
  const byKind = new Map(sourceStates.map((sourceState) => [sourceState.source_kind, sourceState]));
  return dashboardSourceKinds.map((sourceKind) => byKind.get(sourceKind) ?? fallbackSourceState(sourceKind));
}

function fallbackSourceState(sourceKind: SourceKind): SourceState {
  if (apiCostSourceKinds.has(sourceKind)) {
    return {
      source_kind: sourceKind,
      status: "secondary_source",
      confidence: "unavailable"
    };
  }
  return {
    source_kind: sourceKind,
    status: "setup_required",
    confidence: "unavailable"
  };
}

function sourceOrder(sourceKind: SourceKind) {
  return dashboardSourceKinds.indexOf(sourceKind);
}
