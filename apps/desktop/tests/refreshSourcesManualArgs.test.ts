import {
  buildGatedRefreshSourcesManualArgs,
  buildRefreshSourcesManualArgs,
  manualRefreshEndDayUtc
} from "../src/commands/refreshSourcesManualArgs.js";

const valid = buildRefreshSourcesManualArgs({
  endDayUtc: " 2026-06-14 ",
  codexJsonlRoot: " synthetic/codex ",
  claudeCodeJsonlRoot: " ",
  cursorJsonlRoot: " synthetic/cursor ",
  startedAt: " 2026-06-14T00:00:00Z "
});

assert(valid.ok, "expected valid draft to build args");
assertDeepEqual(valid.args, {
  end_day_utc: "2026-06-14",
  codex_jsonl_root: "synthetic/codex",
  cursor_jsonl_root: "synthetic/cursor",
  started_at: "2026-06-14T00:00:00Z"
});
assert(!("claude_code_jsonl_root" in valid.args), "blank optional root should be omitted");

const invalidFormat = buildRefreshSourcesManualArgs({
  endDayUtc: "2026-6-14"
});

assert(!invalidFormat.ok, "expected non-strict date format to fail");
assertDeepEqual(invalidFormat.error, {
  error: {
    code: "invalid_refresh_request",
    field: "end_day_utc",
    message: "end_day_utc must be YYYY-MM-DD"
  }
});

const invalidCalendarDate = buildRefreshSourcesManualArgs({
  endDayUtc: "2026-02-31"
});

assert(!invalidCalendarDate.ok, "expected invalid calendar date to fail");
assertDeepEqual(invalidCalendarDate.error, invalidFormat.error);

const gatedValid = buildGatedRefreshSourcesManualArgs({
  endDayUtc: "2026-06-14",
  githubCopilotJsonlRoot: "synthetic/copilot-report"
});

assert(gatedValid.ok, "expected gated draft with one explicit import root to build args");
assertDeepEqual(gatedValid.args, {
  end_day_utc: "2026-06-14",
  github_copilot_jsonl_root: "synthetic/copilot-report"
});

assert(
  manualRefreshEndDayUtc(new Date("2026-06-14T23:59:59Z")) === "2026-06-14",
  "manual refresh should derive strict UTC day from the current instant"
);
assert(
  manualRefreshEndDayUtc(new Date("2026-06-15T00:00:00Z")) === "2026-06-15",
  "manual refresh should roll the UTC day at UTC midnight"
);

const gatedMissingAnyRoot = buildGatedRefreshSourcesManualArgs({
  endDayUtc: "2026-06-14"
});

assert(!gatedMissingAnyRoot.ok, "expected missing explicit roots to block gated args");
assertDeepEqual(gatedMissingAnyRoot.error, {
  error: {
    code: "invalid_refresh_request",
    field: "codex_jsonl_root",
    message: "at least one source root is required for manual refresh"
  }
});

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
