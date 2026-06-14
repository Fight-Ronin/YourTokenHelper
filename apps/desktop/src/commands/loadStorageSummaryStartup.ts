import type { RefreshStorageSummaryPayload } from "../types.js";
import {
  isStorageSummaryPayload,
  type LoadStorageSummaryResult
} from "./sourceRefreshSummary.js";

export type StartupStorageSummaryOutcome =
  | { ok: true; payload: RefreshStorageSummaryPayload }
  | { ok: false; message: string };

export async function loadStartupStorageSummaryWith(
  load: () => Promise<LoadStorageSummaryResult>
): Promise<StartupStorageSummaryOutcome> {
  try {
    const result = await load();
    if (isStorageSummaryPayload(result)) {
      return { ok: true, payload: result };
    }
    return { ok: false, message: result.error.message };
  } catch {
    return { ok: false, message: "Persisted summary unavailable" };
  }
}
