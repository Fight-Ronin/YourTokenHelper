import {
  invokeRefreshSourcesManualWith,
  type TauriInvoke
} from "../src/commands/refreshSourcesManualInvoker.js";
import {
  REFRESH_SOURCES_MANUAL_COMMAND,
  SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND,
  isRefreshCommandErrorPayload,
  isSourceRefreshSummaryPayload,
  refreshSourcesManualErrorCommandContract,
  sourceRefreshSummarySampleCommandContract
} from "../src/commands/sourceRefreshSummary.js";
import { buildDashboardSummaryFromRefresh } from "../src/data/dashboard-summary.js";
import { manualRefreshSuccessMessage } from "../src/data/source-setup.mock.js";

const calls: { command: string; args?: Record<string, unknown> }[] = [];
const fakeInvoke: TauriInvoke = async <T>(command: string, args?: Record<string, unknown>) => {
  calls.push({ command, args });
  return sourceRefreshSummarySampleCommandContract.result as T;
};

const invoked = await invokeRefreshSourcesManualWith(fakeInvoke, {
  endDayUtc: "2026-06-14",
  codexJsonlRoot: " synthetic/codex ",
  claudeCodeJsonlRoot: " synthetic/claude-code ",
  geminiCliJsonlRoot: " synthetic/gemini "
});

assert(invoked.ok, "expected explicit roots to invoke refresh command");
assert(isSourceRefreshSummaryPayload(invoked.result), "expected success payload from fake invoke");
assert(calls.length === 1, "expected exactly one Tauri invoke call");
assert(calls[0].command === REFRESH_SOURCES_MANUAL_COMMAND, "should invoke production command");
assert(
  String(calls[0].command) !== String(SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND),
  "manual refresh must not invoke the static sample command"
);
assertDeepEqual(calls[0].args, {
  args: {
    end_day_utc: "2026-06-14",
    codex_jsonl_root: "synthetic/codex",
    claude_code_jsonl_root: "synthetic/claude-code",
    gemini_cli_jsonl_root: "synthetic/gemini"
  }
});

const refreshedDashboard = buildDashboardSummaryFromRefresh(invoked.result.storage_summary);
assert(
  refreshedDashboard.summary.totals.total_tokens === 9820,
  "gated refresh success should normalize into the dashboard aggregate total"
);
assert(
  manualRefreshSuccessMessage(refreshedDashboard.summary.totals.total_tokens) ===
    "Updated 9,820 aggregate tokens",
  "gated refresh success should produce the path-free success message"
);
assert(
  !JSON.stringify(refreshedDashboard).includes("synthetic/codex"),
  "dashboard handoff must not expose supplied Codex root values"
);
assert(
  !JSON.stringify(refreshedDashboard).includes("synthetic/claude-code"),
  "dashboard handoff must not expose supplied Claude Code root values"
);

const errorCalls: { command: string; args?: Record<string, unknown> }[] = [];
const fakeErrorInvoke: TauriInvoke = async <T>(command: string, args?: Record<string, unknown>) => {
  errorCalls.push({ command, args });
  return refreshSourcesManualErrorCommandContract.result as T;
};
const structuredError = await invokeRefreshSourcesManualWith(fakeErrorInvoke, {
  endDayUtc: "2026-06-14",
  codexJsonlRoot: "synthetic/codex",
  claudeCodeJsonlRoot: "synthetic/claude-code"
});

assert(structuredError.ok, "structured command errors should still be returned as Tauri invoke results");
assert(isRefreshCommandErrorPayload(structuredError.result), "expected structured error result from fake invoke");
assert(errorCalls.length === 1, "structured command error should still invoke Tauri once");
assert(errorCalls[0].command === REFRESH_SOURCES_MANUAL_COMMAND, "structured command error should use production command");
assert(
  String(errorCalls[0].command) !== String(SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND),
  "structured command error path must not invoke the static sample command"
);
assert(
  !JSON.stringify(structuredError).includes("synthetic/codex"),
  "structured command errors must not echo supplied Codex root values"
);
assert(
  !JSON.stringify(structuredError).includes("synthetic/claude-code"),
  "structured command errors must not echo supplied Claude Code root values"
);

const missingRoot = await invokeRefreshSourcesManualWith(fakeInvoke, {
  endDayUtc: "2026-06-14"
});

assert(!missingRoot.ok, "missing every explicit root should not invoke Tauri");
assert(calls.length === 1, "invalid gated args must not call Tauri invoke");
assertDeepEqual(missingRoot.error, {
  error: {
    code: "invalid_refresh_request",
    field: "codex_jsonl_root",
    message: "at least one source root is required for manual refresh"
  }
});
assert(
  !JSON.stringify(missingRoot).includes("synthetic"),
  "invalid gated args must not echo supplied root values"
);

const thrownInvoke: TauriInvoke = async () => {
  throw new Error("C:/Users/example/secret/usage.sqlite");
};
const thrown = await invokeRefreshSourcesManualWith(thrownInvoke, {
  endDayUtc: "2026-06-14",
  codexJsonlRoot: "synthetic/codex",
  claudeCodeJsonlRoot: "synthetic/claude-code"
});

assert(!thrown.ok, "thrown Tauri failures should return a structured unavailable state");
assertDeepEqual(thrown.error, {
  error: {
    code: "refresh_unavailable",
    message: "Manual refresh unavailable"
  }
});
assert(
  !JSON.stringify(thrown).includes("C:/Users/example/secret/usage.sqlite"),
  "thrown Tauri failures must not reflect local paths or exception text"
);

function assert(condition: unknown, message: string): asserts condition {
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
