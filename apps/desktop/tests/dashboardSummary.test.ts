import { sourceRefreshSummarySampleCommandContract } from "../src/commands/sourceRefreshSummary.js";
import {
  buildDashboardSummaryFromRefresh,
  dashboardQualityLabel,
  emptyTokenTotals,
  latestSummaryDay,
  refreshRecencyLabel,
  sourceUsageRows,
  sourceTotalsForDay,
  startupStorageStatusLabel
} from "../src/data/dashboard-summary.js";

const dashboardPayload = buildDashboardSummaryFromRefresh(
  sourceRefreshSummarySampleCommandContract.result.storage_summary
);

assert(dashboardPayload.generated_from === "backend.sources.refresh", "live dashboard should keep refresh provenance");
assert(!dashboardPayload.privacy.synthetic, "live dashboard should not be labeled synthetic");
assert(
  dashboardPayload.refresh_state.last_status === "succeeded",
  "live dashboard should carry refresh recency status"
);
assert(
  dashboardPayload.refresh_state.successful_source_count === 5,
  "live dashboard should carry ready source count"
);
assert(dashboardPayload.summary.by_source.codex.total_tokens === 2540, "Codex totals should survive normalization");
assert(
  dashboardPayload.summary.by_source.claude_code.total_tokens === 5030,
  "Claude Code totals should survive normalization"
);
assertDeepEqual(
  dashboardPayload.summary.by_source.openai_api_cost,
  emptyTokenTotals(),
  "OpenAI API cost should be an explicit empty secondary source until PR6"
);
assertDeepEqual(
  dashboardPayload.summary.by_source.claude_api_cost,
  emptyTokenTotals(),
  "Claude API cost should be an explicit empty secondary source until provider coverage is verified"
);
assertDeepEqual(
  dashboardPayload.summary.by_source.gemini_api_cost,
  emptyTokenTotals(),
  "Gemini API cost should be an explicit empty secondary source until provider coverage is verified"
);
assertDeepEqual(
  dashboardPayload.summary.by_source.deepseek_api_cost,
  emptyTokenTotals(),
  "DeepSeek API cost should be an explicit empty secondary source until provider coverage is verified"
);
assert(
  dashboardPayload.source_states.find((sourceState) => sourceState.source_kind === "openai_api_cost")?.status ===
    "secondary_source",
  "OpenAI API cost should stay secondary instead of pretending PR5 synced costs"
);
assert(
  dashboardPayload.source_states.find((sourceState) => sourceState.source_kind === "openai_api_cost")?.confidence ===
    "unavailable",
  "OpenAI API cost confidence should stay unavailable after local refresh"
);
for (const sourceKind of ["claude_api_cost", "gemini_api_cost", "deepseek_api_cost"] as const) {
  const sourceState = dashboardPayload.source_states.find((item) => item.source_kind === sourceKind);
  assert(sourceState?.status === "secondary_source", `${sourceKind} should stay secondary after local refresh`);
  assert(sourceState.confidence === "unavailable", `${sourceKind} should stay unavailable after local refresh`);
}
assert(latestSummaryDay(dashboardPayload) === "2026-06-14", "latest day should come from refresh by_day keys");
assert(
  sourceTotalsForDay(dashboardPayload, "2026-06-14").codex.total_tokens === 2540,
  "daily source totals should come from the selected day, not the whole rolling window"
);
assertDeepEqual(
  sourceTotalsForDay(dashboardPayload, "2026-06-13").codex,
  emptyTokenTotals(),
  "missing daily source totals should stay explicit zeroes"
);
assertDeepEqual(
  sourceUsageRows(sourceTotalsForDay(dashboardPayload, "2026-06-14"), ["codex", "claude_code"]).map(
    (row) => row.sourceKind
  ),
  ["claude_code", "codex", "cursor", "github_copilot", "gemini_cli"],
  "Source Usage rows should hide unavailable zero-token sources after local refresh"
);
const liveUsageRows = sourceUsageRows(sourceTotalsForDay(dashboardPayload, "2026-06-14"), ["codex", "claude_code"]);
assert(
  liveUsageRows.every((row) => row.progress.kind === "usage_share"),
  "Source Usage rows should use consumption share bars when no allowance windows are available"
);
assert(
  Math.round(liveUsageRows.find((row) => row.sourceKind === "claude_code")?.progress.percent ?? 0) === 30,
  "Source Usage rows should still show non-zero usage share when limits are unavailable"
);
assert(
  sourceUsageRows(dashboardPayload.summary.by_source, []).every((row) => row.sourceKind !== "openai_api_cost"),
  "Source Usage rows should exclude API cost providers"
);
assertDeepEqual(
  sourceUsageRows(sourceTotalsForDay(dashboardPayload, "2026-06-13"), ["codex"]).map((row) => row.sourceKind),
  ["codex"],
  "configured roots should remain visible even when the selected day has no tokens"
);

const totalsWithConfiguredLowUsage = sourceTotalsForDay(dashboardPayload, "2026-06-13");
totalsWithConfiguredLowUsage.codex = {
  ...emptyTokenTotals(),
  input_tokens: 10,
  total_tokens: 10
};
totalsWithConfiguredLowUsage.cursor = {
  ...emptyTokenTotals(),
  input_tokens: 100,
  total_tokens: 100
};
assertDeepEqual(
  sourceUsageRows(totalsWithConfiguredLowUsage, ["codex"]).map((row) => row.sourceKind),
  ["codex", "cursor"],
  "configured roots should be grouped above unconfigured sources with usage"
);
const quotaRows = sourceUsageRows(
  {
    ...sourceTotalsForDay(dashboardPayload, "2026-06-13"),
    codex: {
      ...emptyTokenTotals(),
      total_tokens: 25
    },
    claude_code: {
      ...emptyTokenTotals(),
      total_tokens: 500
    },
    cursor: {
      ...emptyTokenTotals(),
      total_tokens: 100
    }
  },
  [],
  [
    {
      source_kind: "codex",
      source_id: "codex:test",
      status: "manual",
      unit: "tokens",
      remaining_amount: 75
    },
    {
      source_kind: "claude_code",
      source_id: "claude_code:test",
      status: "derived",
      unit: "credits",
      used_amount: 5,
      remaining_amount: 15
    },
    {
      source_kind: "cursor",
      source_id: "cursor:test",
      status: "unavailable",
      unit: "unknown"
    }
  ]
);
assertDeepEqual(
  quotaRows.find((row) => row.sourceKind === "codex")?.progress,
  {
    kind: "quota",
    percent: 25,
    usedAmount: 25,
    limitAmount: 100,
    unit: "tokens",
    status: "manual"
  },
  "token allowance progress should use token totals when used_amount is not stored"
);
assertDeepEqual(
  quotaRows.find((row) => row.sourceKind === "claude_code")?.progress,
  {
    kind: "quota",
    percent: 25,
    usedAmount: 5,
    limitAmount: 20,
    unit: "credits",
    status: "derived"
  },
  "non-token allowance progress should use allowance units without converting tokens"
);
assertDeepEqual(
  quotaRows.find((row) => row.sourceKind === "cursor")?.progress,
  {
    kind: "usage_share",
    percent: 16
  },
  "unavailable allowance should render usage share instead of a fake quota bar"
);
const tinyUsageRows = sourceUsageRows({
  ...sourceTotalsForDay(dashboardPayload, "2026-06-13"),
  codex: {
    ...emptyTokenTotals(),
    total_tokens: 1
  },
  claude_code: {
    ...emptyTokenTotals(),
    total_tokens: 999
  }
});
assert(
  tinyUsageRows.find((row) => row.sourceKind === "codex")?.progress.percent === 0.1,
  "usage share percent should keep the true value instead of using the visual minimum bar width"
);
assertDeepEqual(
  sourceUsageRows(
    sourceTotalsForDay(dashboardPayload, "2026-06-13"),
    ["codex"],
    [
      {
        source_kind: "codex",
        source_id: "codex:test",
        status: "manual",
        unit: "tokens",
        remaining_amount: 100
      }
    ]
  ).find((row) => row.sourceKind === "codex")?.progress,
  {
    kind: "quota",
    percent: 0,
    usedAmount: 0,
    limitAmount: 100,
    unit: "tokens",
    status: "manual"
  },
  "zero token usage with a token allowance should still render 0% quota progress"
);
assertDeepEqual(
  sourceUsageRows(
    {
      ...sourceTotalsForDay(dashboardPayload, "2026-06-13"),
      codex: {
        ...emptyTokenTotals(),
        total_tokens: 125
      }
    },
    [],
    [
      {
        source_kind: "codex",
        source_id: "codex:test",
        status: "manual",
        unit: "tokens",
        limit_amount: 100
      }
    ]
  ).find((row) => row.sourceKind === "codex")?.progress,
  {
    kind: "quota",
    percent: 125,
    usedAmount: 125,
    limitAmount: 100,
    unit: "tokens",
    status: "manual"
  },
  "quota percent should keep the true over-limit value while the UI caps only the bar width"
);

const copiedDailyTotals = sourceTotalsForDay(dashboardPayload, "2026-06-14");
copiedDailyTotals.codex.total_tokens = 999999;
assert(
  dashboardPayload.summary.by_day_source["2026-06-14"].codex.total_tokens === 2540,
  "daily source totals should be copied before display helpers can mutate them"
);
assert(
  dashboardQualityLabel("mock", { phase: "idle" }) === "Mock data",
  "idle mock dashboard should keep the mock quality label"
);
assert(
  dashboardQualityLabel("mock", { phase: "loading" }) === "Loading saved aggregate",
  "startup readback loading should be visible before persisted data loads"
);
assert(
  dashboardQualityLabel("mock", { phase: "unavailable", message: "unavailable" }) === "Mock data",
  "unavailable startup readback should fall back to mock quality"
);
assert(
  dashboardQualityLabel("local_refresh", { phase: "loading" }) === "Live local aggregate",
  "local aggregate mode should keep the live quality label even if startup readback is still loading"
);
assert(startupStorageStatusLabel({ phase: "idle" }) === "Idle", "idle startup readback should be labeled");
assert(startupStorageStatusLabel({ phase: "loading" }) === "Checking", "loading startup readback should be labeled");
assert(startupStorageStatusLabel({ phase: "loaded" }) === "Loaded", "loaded startup readback should be labeled");
assert(
  startupStorageStatusLabel({ phase: "unavailable", message: "unavailable" }) === "Unavailable",
  "unavailable startup readback should be labeled"
);
assertDeepEqual(
  refreshRecencyLabel(dashboardPayload.refresh_state, new Date("2026-06-14T00:10:00Z")),
  {
    label: "Fresh",
    detail: "refreshed 10 min ago across 5 ready sources",
    tone: "good"
  },
  "recent successful refresh should be fresh"
);
assertDeepEqual(
  refreshRecencyLabel(dashboardPayload.refresh_state, new Date("2026-06-14T01:01:00Z")),
  {
    label: "Stale",
    detail: "refreshed 1 hr ago across 5 ready sources",
    tone: "warning"
  },
  "older successful refresh should be stale"
);
assertDeepEqual(
  refreshRecencyLabel(
    {
      last_attempt_at: null,
      last_success_at: null,
      last_status: "never_refreshed",
      successful_source_count: 0,
      attempted_source_count: 0,
      events_seen: 0
    },
    new Date("2026-06-14T01:01:00Z")
  ),
  {
    label: "Never refreshed",
    detail: "No successful local aggregate refresh yet",
    tone: "warning"
  },
  "missing successful refresh should not pretend the aggregate is fresh"
);
assertDeepEqual(
  refreshRecencyLabel(
    {
      last_attempt_at: "2026-06-14T00:00:00Z",
      last_success_at: "2026-06-14T00:00:00Z",
      last_status: "mock",
      successful_source_count: 0,
      attempted_source_count: 0,
      events_seen: 0
    },
    new Date("2026-06-14T00:10:00Z")
  ),
  {
    label: "Mock fixture",
    detail: "Static contract data, not a local refresh",
    tone: "neutral"
  },
  "mock payload should not be labeled as a live refresh"
);

const serialized = JSON.stringify(dashboardPayload);
assert(!serialized.includes("C:/Users"), "dashboard payload must not expose local user paths");
assert(!serialized.includes("source_root"), "dashboard payload must not expose source roots");
assert(!serialized.includes("source_path"), "dashboard payload must not expose source paths");
assert(!serialized.includes("secret"), "dashboard payload must not expose secret path markers");

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function assertDeepEqual(actual: unknown, expected: unknown, message: string) {
  const actualJson = JSON.stringify(actual);
  const expectedJson = JSON.stringify(expected);
  if (actualJson !== expectedJson) {
    throw new Error(`${message}: expected ${expectedJson}, got ${actualJson}`);
  }
}
