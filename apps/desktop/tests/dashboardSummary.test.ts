import { sourceRefreshSummarySampleCommandContract } from "../src/commands/sourceRefreshSummary.js";
import {
  buildDashboardSummaryFromRefresh,
  dashboardQualityLabel,
  emptyTokenTotals,
  latestSummaryDay,
  sourceUsageRows,
  sourceTotalsForDay,
  startupStorageStatusLabel
} from "../src/data/dashboard-summary.js";

const dashboardPayload = buildDashboardSummaryFromRefresh(
  sourceRefreshSummarySampleCommandContract.result.storage_summary
);

assert(dashboardPayload.generated_from === "backend.sources.refresh", "live dashboard should keep refresh provenance");
assert(!dashboardPayload.privacy.synthetic, "live dashboard should not be labeled synthetic");
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
  ["claude_code", "codex"],
  "Source Usage rows should hide unavailable zero-token sources after local refresh"
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
