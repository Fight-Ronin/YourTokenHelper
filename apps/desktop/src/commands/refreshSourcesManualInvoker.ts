import {
  buildGatedRefreshSourcesManualArgs,
  type RefreshCommandErrorPayload,
  type RefreshSourcesManualDraft
} from "./refreshSourcesManualArgs.js";
import {
  REFRESH_SOURCES_MANUAL_COMMAND,
  type RefreshSourcesManualResult
} from "./sourceRefreshSummary.js";

export type TauriInvoke = <T>(command: string, args?: Record<string, unknown>) => Promise<T>;

export type RefreshSourcesManualInvokeOutcome =
  | {
      ok: true;
      result: RefreshSourcesManualResult;
    }
  | {
      ok: false;
      error: RefreshCommandErrorPayload;
    };

export async function invokeRefreshSourcesManualWith(
  tauriInvoke: TauriInvoke,
  draft: RefreshSourcesManualDraft
): Promise<RefreshSourcesManualInvokeOutcome> {
  const builtArgs = buildGatedRefreshSourcesManualArgs(draft);
  if (!builtArgs.ok) {
    return {
      ok: false,
      error: builtArgs.error
    };
  }

  try {
    return {
      ok: true,
      result: await tauriInvoke<RefreshSourcesManualResult>(REFRESH_SOURCES_MANUAL_COMMAND, {
        args: builtArgs.args
      })
    };
  } catch {
    return {
      ok: false,
      error: {
        error: {
          code: "refresh_unavailable",
          message: "Manual refresh unavailable"
        }
      }
    };
  }
}
