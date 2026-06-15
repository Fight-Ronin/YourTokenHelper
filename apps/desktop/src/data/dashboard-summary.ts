import type {
  AllowanceWindow,
  MockSummaryPayload,
  RefreshState,
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
  progress: SourceUsageProgress;
};
export type SourceUsageProgress =
  | {
      kind: "quota";
      percent: number;
      usedAmount: number;
      limitAmount: number;
      unit: AllowanceWindow["unit"];
      status: AllowanceWindow["status"];
    }
  | {
      kind: "usage_share";
      percent: number;
    };

export type DashboardDataMode = "mock" | "local_refresh";
export type StartupStorageReadState =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "loaded" }
  | { phase: "unavailable"; message: string };
export type RefreshRecency = {
  label: string;
  detail: string;
  tone: "neutral" | "good" | "warning";
};

const refreshStaleAfterMinutes = 30;

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
  configuredSourceKinds: readonly SourceKind[] = [],
  allowanceWindows: readonly AllowanceWindow[] = []
): SourceUsageRow[] {
  const configuredKinds = new Set(configuredSourceKinds);
  const allowancesBySource = new Map(allowanceWindows.map((window) => [window.source_kind, window]));

  const visibleEntries = Object.entries(totals)
    .filter(([sourceKind, tokenTotals]) => {
      if (apiCostSourceKinds.has(sourceKind as SourceKind)) {
        return false;
      }
      return tokenTotals.total_tokens > 0 || configuredKinds.has(sourceKind as SourceKind);
    });
  const visibleTotal = visibleEntries.reduce((total, [, tokenTotals]) => total + tokenTotals.total_tokens, 0);

  return visibleEntries
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
      totals: tokenTotals,
      progress: sourceUsageProgress(
        tokenTotals,
        allowancesBySource.get(sourceKind as SourceKind),
        usageSharePercent(tokenTotals.total_tokens, visibleTotal)
      )
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

export function refreshRecencyLabel(
  state: RefreshState,
  now: Date = new Date(),
  staleAfterMinutes = refreshStaleAfterMinutes
): RefreshRecency {
  if (state.last_status === "mock") {
    return {
      label: "Mock fixture",
      detail: "Static contract data, not a local refresh",
      tone: "neutral"
    };
  }
  if (!state.last_success_at) {
    const label =
      state.last_status === "blocked"
        ? "Needs setup"
        : state.last_status === "failed"
          ? "Refresh failed"
          : "Never refreshed";
    return {
      label,
      detail: "No successful local aggregate refresh yet",
      tone: "warning"
    };
  }

  const ageMinutes = refreshAgeMinutes(state.last_success_at, now);
  const isStale = ageMinutes === null || ageMinutes > staleAfterMinutes;
  if (state.last_status === "partial") {
    return {
      label: isStale ? "Partial stale" : "Partial refresh",
      detail: `${formatRefreshAge(state.last_success_at, now)} across ${state.successful_source_count} ready sources`,
      tone: "warning"
    };
  }
  if (state.last_status === "failed") {
    return {
      label: "Refresh failed",
      detail: `Last success ${formatRefreshAge(state.last_success_at, now)}`,
      tone: "warning"
    };
  }
  return {
    label: isStale ? "Stale" : "Fresh",
    detail: `${formatRefreshAge(state.last_success_at, now)} across ${state.successful_source_count} ready sources`,
    tone: isStale ? "warning" : "good"
  };
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

function sourceUsageProgress(
  totals: TokenTotals,
  allowanceWindow: AllowanceWindow | undefined,
  usageShare: number
): SourceUsageProgress {
  if (!allowanceWindow || allowanceWindow.status === "unavailable") {
    return { kind: "usage_share", percent: usageShare };
  }

  const usedAmount = knownNumber(allowanceWindow.used_amount)
    ?? (allowanceWindow.unit === "tokens" ? totals.total_tokens : undefined);
  const remainingAmount = knownNumber(allowanceWindow.remaining_amount);
  const limitAmount = knownNumber(allowanceWindow.limit_amount)
    ?? (usedAmount !== undefined && remainingAmount !== undefined ? usedAmount + remainingAmount : undefined);
  if (usedAmount === undefined || limitAmount === undefined || limitAmount <= 0) {
    return { kind: "usage_share", percent: usageShare };
  }

  return {
    kind: "quota",
    percent: Math.max(0, (usedAmount / limitAmount) * 100),
    usedAmount,
    limitAmount,
    unit: allowanceWindow.unit,
    status: allowanceWindow.status
  };
}

function usageSharePercent(value: number, total: number) {
  if (value <= 0 || total <= 0) {
    return 0;
  }
  return Math.min(100, (value / total) * 100);
}

function knownNumber(value: number | undefined) {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function refreshAgeMinutes(isoTimestamp: string, now: Date) {
  const timestamp = new Date(isoTimestamp).getTime();
  if (!Number.isFinite(timestamp)) {
    return null;
  }
  const diffMs = Math.max(0, now.getTime() - timestamp);
  return Math.floor(diffMs / 60000);
}

function formatRefreshAge(isoTimestamp: string, now: Date) {
  const ageMinutes = refreshAgeMinutes(isoTimestamp, now);
  if (ageMinutes === null) {
    return "refresh time unavailable";
  }
  if (ageMinutes < 1) {
    return "refreshed just now";
  }
  if (ageMinutes < 60) {
    return `refreshed ${ageMinutes} min ago`;
  }
  const ageHours = Math.floor(ageMinutes / 60);
  if (ageHours < 24) {
    return `refreshed ${ageHours} hr ago`;
  }
  const ageDays = Math.floor(ageHours / 24);
  return `refreshed ${ageDays} day${ageDays === 1 ? "" : "s"} ago`;
}
