export type RefreshSourcesManualArgs = {
  end_day_utc: string;
  codex_jsonl_root?: string;
  claude_code_jsonl_root?: string;
  started_at?: string;
};

export type RefreshSourcesManualDraft = {
  endDayUtc: string;
  codexJsonlRoot?: string;
  claudeCodeJsonlRoot?: string;
  startedAt?: string;
};

export type RefreshCommandErrorPayload = {
  error: {
    code: "invalid_refresh_request" | "refresh_unavailable";
    message: string;
    field?: keyof RefreshSourcesManualArgs;
  };
};

export type RefreshSourcesManualArgsBuildResult =
  | {
      ok: true;
      args: RefreshSourcesManualArgs;
    }
  | {
      ok: false;
      error: RefreshCommandErrorPayload;
    };

const UTC_DAY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

export function buildRefreshSourcesManualArgs(
  draft: RefreshSourcesManualDraft
): RefreshSourcesManualArgsBuildResult {
  const endDayUtc = draft.endDayUtc.trim();
  if (!isStrictUtcDay(endDayUtc)) {
    return invalidRefreshArgs("end_day_utc", "end_day_utc must be YYYY-MM-DD");
  }

  const args: RefreshSourcesManualArgs = {
    end_day_utc: endDayUtc
  };
  assignOptionalString(args, "codex_jsonl_root", draft.codexJsonlRoot);
  assignOptionalString(args, "claude_code_jsonl_root", draft.claudeCodeJsonlRoot);
  assignOptionalString(args, "started_at", draft.startedAt);

  return {
    ok: true,
    args
  };
}

export function buildGatedRefreshSourcesManualArgs(
  draft: RefreshSourcesManualDraft
): RefreshSourcesManualArgsBuildResult {
  const result = buildRefreshSourcesManualArgs(draft);
  if (!result.ok) {
    return result;
  }
  if (!result.args.codex_jsonl_root) {
    return invalidRefreshArgs("codex_jsonl_root", "codex_jsonl_root is required for manual refresh");
  }
  if (!result.args.claude_code_jsonl_root) {
    return invalidRefreshArgs(
      "claude_code_jsonl_root",
      "claude_code_jsonl_root is required for manual refresh"
    );
  }
  return result;
}

export function manualRefreshEndDayUtc(now = new Date()) {
  return now.toISOString().slice(0, 10);
}

function invalidRefreshArgs(
  field: keyof RefreshSourcesManualArgs,
  message: string
): RefreshSourcesManualArgsBuildResult {
  return {
    ok: false,
    error: {
      error: {
        code: "invalid_refresh_request",
        field,
        message
      }
    }
  };
}

function assignOptionalString(
  args: RefreshSourcesManualArgs,
  field: Exclude<keyof RefreshSourcesManualArgs, "end_day_utc">,
  value: string | undefined
) {
  const normalized = value?.trim();
  if (normalized) {
    args[field] = normalized;
  }
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
