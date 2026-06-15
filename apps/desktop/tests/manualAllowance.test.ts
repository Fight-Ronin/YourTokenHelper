import {
  SAVE_MANUAL_ALLOWANCE_WINDOW_COMMAND,
  buildManualAllowanceArgs,
  defaultManualAllowanceEndDayUtc,
  invokeSaveManualAllowanceWith,
  isManualAllowanceSuccessPayload,
  type ManualAllowanceResult
} from "../src/commands/manualAllowance.js";
import {
  REFRESH_SOURCES_MANUAL_COMMAND,
  SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND,
  sourceRefreshSummarySampleCommandContract
} from "../src/commands/sourceRefreshSummary.js";
import type { TauriInvoke } from "../src/commands/refreshSourcesManualInvoker.js";
import {
  buildDashboardSummaryFromRefresh,
  emptyTokenTotals,
  sourceUsageRows
} from "../src/data/dashboard-summary.js";

const allowanceWindow = {
  source_kind: "codex",
  source_id: "codex:manual_allowance",
  status: "manual",
  unit: "tokens",
  limit_amount: 100000,
  remaining_amount: 97460,
  reset_at: "2026-06-21T00:00:00Z"
} as const;

const manualAllowanceSuccess: ManualAllowanceResult = {
  allowance_window: allowanceWindow,
  storage_summary: {
    ...sourceRefreshSummarySampleCommandContract.result.storage_summary,
    allowance_windows: [allowanceWindow]
  }
};

assert(
  SAVE_MANUAL_ALLOWANCE_WINDOW_COMMAND === "save_manual_allowance_window",
  "manual allowance command name should match backend contract"
);
assert(
  String(SAVE_MANUAL_ALLOWANCE_WINDOW_COMMAND) !== String(SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND),
  "manual allowance must stay separate from the static sample command"
);
assert(
  String(SAVE_MANUAL_ALLOWANCE_WINDOW_COMMAND) !== String(REFRESH_SOURCES_MANUAL_COMMAND),
  "manual allowance must stay separate from source refresh"
);

const builtArgs = buildManualAllowanceArgs({
  endDayUtc: "2026-06-14",
  sourceKind: "codex",
  limitAmount: 100000,
  remainingAmount: 97460,
  resetAt: " 2026-06-21T00:00:00Z "
});
assert(builtArgs.ok, "valid manual allowance draft should build command args");
assertDeepEqual(builtArgs.args, {
  end_day_utc: "2026-06-14",
  source_kind: "codex",
  unit: "tokens",
  limit_amount: 100000,
  remaining_amount: 97460,
  reset_at: "2026-06-21T00:00:00Z"
});
assert(
  !JSON.stringify(builtArgs).includes("database_path"),
  "manual allowance args must not include database paths"
);
assert(
  !JSON.stringify(builtArgs).includes("source_id"),
  "manual allowance args must not include user-controlled source ids"
);
assert(
  !JSON.stringify(builtArgs).includes("note"),
  "manual allowance args must not include free-text notes"
);

assertDeepEqual(
  buildManualAllowanceArgs({
    endDayUtc: "2026-6-14",
    sourceKind: "codex",
    limitAmount: 100000
  }),
  {
    ok: false,
    error: {
      error: {
        code: "invalid_manual_allowance_request",
        field: "end_day_utc",
        message: "end_day_utc must be YYYY-MM-DD"
      }
    }
  }
);
assertDeepEqual(
  buildManualAllowanceArgs({
    endDayUtc: "2026-06-14",
    sourceKind: "codex",
    limitAmount: 0
  }),
  {
    ok: false,
    error: {
      error: {
        code: "invalid_manual_allowance_request",
        field: "limit_amount",
        message: "limit_amount must be positive"
      }
    }
  }
);
assertDeepEqual(
  buildManualAllowanceArgs({
    endDayUtc: "2026-06-14",
    sourceKind: "codex",
    limitAmount: 100000,
    usedAmount: -1
  }),
  {
    ok: false,
    error: {
      error: {
        code: "invalid_manual_allowance_request",
        field: "used_amount",
        message: "used_amount must be non-negative"
      }
    }
  }
);
assert(
  defaultManualAllowanceEndDayUtc(new Date("2026-06-15T12:00:00Z")) === "2026-06-15",
  "manual allowance default end day should use the UTC day helper"
);

const calls: { command: string; args?: Record<string, unknown> }[] = [];
const fakeInvoke: TauriInvoke = async <T>(command: string, args?: Record<string, unknown>) => {
  calls.push({ command, args });
  return manualAllowanceSuccess as T;
};

const invoked = await invokeSaveManualAllowanceWith(fakeInvoke, {
  endDayUtc: "2026-06-14",
  sourceKind: "codex",
  limitAmount: 100000,
  remainingAmount: 97460
});
assert(invoked.ok, "valid manual allowance should invoke Tauri");
assert(calls.length === 1, "manual allowance should invoke once");
assert(calls[0].command === SAVE_MANUAL_ALLOWANCE_WINDOW_COMMAND, "should invoke manual allowance command");
assertDeepEqual(calls[0].args, {
  args: {
    end_day_utc: "2026-06-14",
    source_kind: "codex",
    unit: "tokens",
    limit_amount: 100000,
    remaining_amount: 97460
  }
});
if (!invoked.ok || !isManualAllowanceSuccessPayload(invoked.result)) {
  throw new Error("expected manual allowance success payload");
}
const dashboardPayload = buildDashboardSummaryFromRefresh(invoked.result.storage_summary);
const quotaRows = sourceUsageRows(
  {
    ...dashboardPayload.summary.by_source,
    codex: {
      ...emptyTokenTotals(),
      total_tokens: 500
    }
  },
  [],
  dashboardPayload.allowance_windows
);
assertDeepEqual(
  quotaRows.find((row) => row.sourceKind === "codex")?.progress,
  {
    kind: "quota",
    percent: 2.54,
    usedAmount: 2540,
    limitAmount: 100000,
    unit: "tokens",
    status: "manual"
  },
  "manual allowance should derive quota progress from saved limit and remaining before visible token totals"
);
assert(
  !JSON.stringify(dashboardPayload).includes("C:/Users"),
  "dashboard handoff must not expose local paths"
);

const structuredErrorCalls: { command: string; args?: Record<string, unknown> }[] = [];
const structuredErrorInvoke: TauriInvoke = async <T>(command: string, args?: Record<string, unknown>) => {
  structuredErrorCalls.push({ command, args });
  return {
    error: {
      code: "invalid_manual_allowance_request",
      field: "limit_amount",
      message: "limit_amount must be positive"
    }
  } as T;
};
const structuredError = await invokeSaveManualAllowanceWith(structuredErrorInvoke, {
  endDayUtc: "2026-06-14",
  sourceKind: "codex",
  limitAmount: 100000
});
assert(structuredError.ok, "structured backend errors should return as invoke results");
assert(!isManualAllowanceSuccessPayload(structuredError.result), "structured backend error should narrow to error");
assert(structuredErrorCalls.length === 1, "structured backend error should invoke once");

const invalidDraft = await invokeSaveManualAllowanceWith(fakeInvoke, {
  endDayUtc: "2026-06-14",
  sourceKind: "codex",
  limitAmount: Number.NaN
});
assert(!invalidDraft.ok, "invalid local args should not invoke Tauri");
assert(calls.length === 1, "invalid local args must not add another invoke call");
assert(
  !JSON.stringify(invalidDraft).includes("NaN"),
  "invalid local args should not echo invalid numeric values"
);

const thrownInvoke: TauriInvoke = async () => {
  throw new Error("C:/Users/example/secret/usage.sqlite");
};
const thrown = await invokeSaveManualAllowanceWith(thrownInvoke, {
  endDayUtc: "2026-06-14",
  sourceKind: "codex",
  limitAmount: 100000
});
assert(!thrown.ok, "thrown Tauri failures should return unavailable");
assertDeepEqual(thrown.error, {
  error: {
    code: "manual_allowance_unavailable",
    message: "Manual allowance unavailable"
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

function assertDeepEqual(actual: unknown, expected: unknown, message?: string) {
  const actualJson = JSON.stringify(stableValue(actual));
  const expectedJson = JSON.stringify(stableValue(expected));
  if (actualJson !== expectedJson) {
    throw new Error(`${message ? `${message}: ` : ""}expected ${expectedJson}, got ${actualJson}`);
  }
}

function stableValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(stableValue);
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([leftKey], [rightKey]) => leftKey.localeCompare(rightKey))
        .map(([key, item]) => [key, stableValue(item)])
    );
  }
  return value;
}
