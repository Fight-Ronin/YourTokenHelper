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
  "openai_api_cost"
];

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
      by_source: completeSourceTotals(storageSummary.summary.by_source)
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

function completeSourceStates(sourceStates: SourceState[]): SourceState[] {
  const byKind = new Map(sourceStates.map((sourceState) => [sourceState.source_kind, sourceState]));
  return dashboardSourceKinds.map((sourceKind) => byKind.get(sourceKind) ?? fallbackSourceState(sourceKind));
}

function fallbackSourceState(sourceKind: SourceKind): SourceState {
  if (sourceKind === "openai_api_cost") {
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
