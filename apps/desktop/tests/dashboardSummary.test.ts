import { sourceRefreshSummarySampleCommandContract } from "../src/commands/sourceRefreshSummary.js";
import {
  buildDashboardSummaryFromRefresh,
  dashboardQualityLabel,
  emptyTokenTotals,
  latestSummaryDay,
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
assert(latestSummaryDay(dashboardPayload) === "2026-06-14", "latest day should come from refresh by_day keys");
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
