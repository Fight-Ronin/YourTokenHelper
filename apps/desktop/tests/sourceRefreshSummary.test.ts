import {
  LOAD_STORAGE_SUMMARY_COMMAND,
  REFRESH_SOURCES_MANUAL_COMMAND,
  SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND,
  isRefreshCommandErrorPayload,
  isSourceRefreshSummaryPayload,
  isStorageSummaryPayload,
  loadStorageSummaryCommandContract,
  refreshSourcesManualErrorCommandContract,
  refreshSourcesManualCommandContract,
  sourceRefreshSummarySampleCommandContract
} from "../src/commands/sourceRefreshSummary.js";
import { loadStartupStorageSummaryWith } from "../src/commands/loadStorageSummaryStartup.js";

assert(
  SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND === "source_refresh_summary_sample",
  "static sample command name should match Tauri contract"
);
assert(
  REFRESH_SOURCES_MANUAL_COMMAND === "refresh_sources_manual",
  "manual refresh command name should match backend contract"
);
assert(
  LOAD_STORAGE_SUMMARY_COMMAND === "load_storage_summary",
  "storage summary command name should match Tauri contract"
);
assert(
  String(REFRESH_SOURCES_MANUAL_COMMAND) !== String(SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND),
  "manual refresh must stay separate from the static sample command"
);
assert(
  String(LOAD_STORAGE_SUMMARY_COMMAND) !== String(SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND),
  "storage summary load must stay separate from the static sample command"
);
assert(
  String(LOAD_STORAGE_SUMMARY_COMMAND) !== String(REFRESH_SOURCES_MANUAL_COMMAND),
  "storage summary load must stay separate from manual refresh"
);

assert(
  sourceRefreshSummarySampleCommandContract.name === SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND,
  "static sample contract should use the static command name"
);
assert(
  refreshSourcesManualCommandContract.name === REFRESH_SOURCES_MANUAL_COMMAND,
  "manual refresh contract should use the production command name"
);
assert(
  refreshSourcesManualErrorCommandContract.name === REFRESH_SOURCES_MANUAL_COMMAND,
  "manual refresh error contract should use the production command name"
);
assert(
  loadStorageSummaryCommandContract.name === LOAD_STORAGE_SUMMARY_COMMAND,
  "storage summary contract should use the readback command name"
);
assert(
  refreshSourcesManualCommandContract.args.end_day_utc === "2026-06-14",
  "manual refresh contract should include strict end_day_utc args"
);
assert(
  loadStorageSummaryCommandContract.args.end_day_utc === "2026-06-14",
  "storage summary contract should include strict end_day_utc args"
);

assert(
  isSourceRefreshSummaryPayload(sourceRefreshSummarySampleCommandContract.result),
  "static sample result should narrow to success payload"
);
assert(
  !isRefreshCommandErrorPayload(sourceRefreshSummarySampleCommandContract.result),
  "static sample result should not narrow to error payload"
);
assert(
  isRefreshCommandErrorPayload(refreshSourcesManualErrorCommandContract.result),
  "shared invalid refresh result should narrow to error payload"
);
assert(
  !isSourceRefreshSummaryPayload(refreshSourcesManualErrorCommandContract.result),
  "shared invalid refresh result should not narrow to success payload"
);
assert(
  isStorageSummaryPayload(loadStorageSummaryCommandContract.result),
  "storage summary readback result should narrow to storage summary payload"
);
assert(
  !isRefreshCommandErrorPayload(loadStorageSummaryCommandContract.result),
  "storage summary readback sample should not narrow to error payload"
);
assert(
  !JSON.stringify(loadStorageSummaryCommandContract.result).includes("refresh_results"),
  "storage summary readback result must not include refresh metadata"
);
assertDeepEqual(refreshSourcesManualErrorCommandContract.result, {
  error: {
    code: "invalid_refresh_request",
    field: "end_day_utc",
    message: "end_day_utc must be YYYY-MM-DD"
  }
});
assert(
  !JSON.stringify(refreshSourcesManualErrorCommandContract.result).includes("C:/Users"),
  "shared invalid refresh result should not expose local user paths"
);

assertDeepEqual(sourceRefreshSummarySampleCommandContract.result.storage_summary.summary.totals, {
  input_tokens: 6200,
  output_tokens: 1330,
  cached_input_tokens: 1600,
  reasoning_output_tokens: 40,
  total_tokens: 7570
});
assert(
  sourceRefreshSummarySampleCommandContract.result.refresh_results.length === 5,
  "static sample should include all primary source rows"
);
assertDeepEqual(
  sourceRefreshSummarySampleCommandContract.result.refresh_results.map((result) => [
    result.source_kind,
    result.status,
    result.events_seen,
    result.sync_run_id
  ]),
  [
    ["codex", "ready", 2, 1],
    ["claude_code", "ready", 2, 2],
    ["cursor", "manual_only", 0, 3],
    ["gemini_cli", "setup_required", 0, 4],
    ["github_copilot", "official_report", 0, 5]
  ]
);
assert(
  !JSON.stringify(sourceRefreshSummarySampleCommandContract.result.refresh_results).includes("root"),
  "refresh result metadata should not expose roots"
);
assert(
  !JSON.stringify(sourceRefreshSummarySampleCommandContract.result.refresh_results).includes("path"),
  "refresh result metadata should not expose paths"
);

const loadedStartupSummary = await loadStartupStorageSummaryWith(async () => loadStorageSummaryCommandContract.result);
assert(loadedStartupSummary.ok, "startup storage readback should accept storage summary payloads");
assertDeepEqual(loadedStartupSummary.payload.summary.totals, {
  input_tokens: 6200,
  output_tokens: 1330,
  cached_input_tokens: 1600,
  reasoning_output_tokens: 40,
  total_tokens: 7570
});

const unavailableStartupSummary = await loadStartupStorageSummaryWith(async () => ({
  error: {
    code: "storage_summary_unavailable",
    field: "database_path",
    message: "storage summary database is unavailable"
  }
}));
assert(!unavailableStartupSummary.ok, "startup storage readback should keep structured unavailable states");
assert(
  unavailableStartupSummary.message === "storage summary database is unavailable",
  "structured unavailable state should use backend redacted message"
);
assert(
  !JSON.stringify(unavailableStartupSummary).includes("database_path"),
  "startup unavailable outcome should not expose internal database fields"
);

const thrownStartupSummary = await loadStartupStorageSummaryWith(async () => {
  throw new Error("C:/Users/example/secret/usage.sqlite");
});
assert(!thrownStartupSummary.ok, "startup storage readback should handle thrown Tauri/browser failures");
assert(
  thrownStartupSummary.message === "Persisted summary unavailable",
  "thrown startup failures should not reflect local paths or exception text"
);

function assert(condition: boolean, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function assertDeepEqual(actual: unknown, expected: unknown) {
  const actualJson = JSON.stringify(actual);
  const expectedJson = JSON.stringify(expected);
  if (actualJson !== expectedJson) {
    throw new Error(`expected ${expectedJson}, got ${actualJson}`);
  }
}
