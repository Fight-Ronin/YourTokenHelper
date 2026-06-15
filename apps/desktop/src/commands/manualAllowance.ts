import { invoke } from "@tauri-apps/api/core";

import type { AllowanceWindow, RefreshStorageSummaryPayload, SourceKind } from "../types.js";
import { manualRefreshEndDayUtc, type CommandErrorPayload } from "./sourceRefreshSummary.js";
import type { TauriInvoke } from "./refreshSourcesManualInvoker.js";

export const SAVE_MANUAL_ALLOWANCE_WINDOW_COMMAND = "save_manual_allowance_window" as const;

export type ManualAllowanceArgs = {
  end_day_utc: string;
  source_kind: SourceKind;
  unit?: AllowanceWindow["unit"];
  limit_amount: number;
  used_amount?: number;
  remaining_amount?: number;
  window_start?: string;
  window_end?: string;
  reset_at?: string;
};

export type ManualAllowanceDraft = {
  endDayUtc: string;
  sourceKind: SourceKind;
  unit?: AllowanceWindow["unit"];
  limitAmount: number;
  usedAmount?: number;
  remainingAmount?: number;
  windowStart?: string;
  windowEnd?: string;
  resetAt?: string;
};

export type ManualAllowanceSuccessPayload = {
  allowance_window: AllowanceWindow;
  storage_summary: RefreshStorageSummaryPayload;
};

export type ManualAllowanceResult = ManualAllowanceSuccessPayload | CommandErrorPayload;

export type ManualAllowanceArgsBuildResult =
  | {
      ok: true;
      args: ManualAllowanceArgs;
    }
  | {
      ok: false;
      error: CommandErrorPayload;
    };

export type ManualAllowanceInvokeOutcome =
  | {
      ok: true;
      result: ManualAllowanceResult;
    }
  | {
      ok: false;
      error: CommandErrorPayload;
    };

const UTC_DAY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const sourceKinds = new Set<SourceKind>([
  "codex",
  "claude_code",
  "gemini_cli",
  "openai_api_cost",
  "claude_api_cost",
  "gemini_api_cost",
  "deepseek_api_cost"
]);
const allowanceUnits = new Set<AllowanceWindow["unit"]>([
  "tokens",
  "credits",
  "usd",
  "requests",
  "unknown"
]);

export function buildManualAllowanceArgs(
  draft: ManualAllowanceDraft
): ManualAllowanceArgsBuildResult {
  const endDayUtc = draft.endDayUtc.trim();
  if (!isStrictUtcDay(endDayUtc)) {
    return invalidManualAllowanceArgs("end_day_utc", "end_day_utc must be YYYY-MM-DD");
  }
  if (!sourceKinds.has(draft.sourceKind)) {
    return invalidManualAllowanceArgs("source_kind", "unknown source_kind");
  }
  const unit = draft.unit ?? "tokens";
  if (!allowanceUnits.has(unit)) {
    return invalidManualAllowanceArgs("unit", "unknown allowance unit");
  }
  if (!Number.isFinite(draft.limitAmount) || draft.limitAmount <= 0) {
    return invalidManualAllowanceArgs("limit_amount", "limit_amount must be positive");
  }

  const args: ManualAllowanceArgs = {
    end_day_utc: endDayUtc,
    source_kind: draft.sourceKind,
    unit,
    limit_amount: draft.limitAmount
  };
  if (!assignOptionalNumber(args, "used_amount", draft.usedAmount)) {
    return invalidManualAllowanceArgs("used_amount", "used_amount must be non-negative");
  }
  if (!assignOptionalNumber(args, "remaining_amount", draft.remainingAmount)) {
    return invalidManualAllowanceArgs("remaining_amount", "remaining_amount must be non-negative");
  }
  assignOptionalString(args, "window_start", draft.windowStart);
  assignOptionalString(args, "window_end", draft.windowEnd);
  assignOptionalString(args, "reset_at", draft.resetAt);

  return { ok: true, args };
}

export async function invokeSaveManualAllowanceWith(
  tauriInvoke: TauriInvoke,
  draft: ManualAllowanceDraft
): Promise<ManualAllowanceInvokeOutcome> {
  const builtArgs = buildManualAllowanceArgs(draft);
  if (!builtArgs.ok) {
    return {
      ok: false,
      error: builtArgs.error
    };
  }

  try {
    return {
      ok: true,
      result: await tauriInvoke<ManualAllowanceResult>(SAVE_MANUAL_ALLOWANCE_WINDOW_COMMAND, {
        args: builtArgs.args
      })
    };
  } catch {
    return {
      ok: false,
      error: {
        error: {
          code: "manual_allowance_unavailable",
          message: "Manual allowance unavailable"
        }
      }
    };
  }
}

export function invokeSaveManualAllowance(
  draft: ManualAllowanceDraft
): Promise<ManualAllowanceInvokeOutcome> {
  return invokeSaveManualAllowanceWith(invoke, draft);
}

export function isManualAllowanceSuccessPayload(
  result: ManualAllowanceResult
): result is ManualAllowanceSuccessPayload {
  return !("error" in result);
}

export function defaultManualAllowanceEndDayUtc(now = new Date()) {
  return manualRefreshEndDayUtc(now);
}

function assignOptionalNumber(
  args: ManualAllowanceArgs,
  field: "used_amount" | "remaining_amount",
  value: number | undefined
) {
  if (value === undefined) {
    return true;
  }
  if (!Number.isFinite(value) || value < 0) {
    return false;
  }
  args[field] = value;
  return true;
}

function assignOptionalString(
  args: ManualAllowanceArgs,
  field: "window_start" | "window_end" | "reset_at",
  value: string | undefined
) {
  const normalized = value?.trim();
  if (normalized) {
    args[field] = normalized;
  }
}

function invalidManualAllowanceArgs(
  field: keyof ManualAllowanceArgs,
  message: string
): ManualAllowanceArgsBuildResult {
  return {
    ok: false,
    error: {
      error: {
        code: "invalid_manual_allowance_request",
        field,
        message
      }
    }
  };
}

function isStrictUtcDay(value: string) {
  if (!UTC_DAY_PATTERN.test(value)) {
    return false;
  }
  const [year, month, day] = value.split("-").map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return (
    parsed.getUTCFullYear() === year &&
    parsed.getUTCMonth() === month - 1 &&
    parsed.getUTCDate() === day
  );
}
