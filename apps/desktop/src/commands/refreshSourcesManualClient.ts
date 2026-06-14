import { invoke } from "@tauri-apps/api/core";

import type { RefreshSourcesManualDraft } from "./refreshSourcesManualArgs.js";
import {
  invokeRefreshSourcesManualWith,
  type RefreshSourcesManualInvokeOutcome
} from "./refreshSourcesManualInvoker.js";

export function invokeRefreshSourcesManual(
  draft: RefreshSourcesManualDraft
): Promise<RefreshSourcesManualInvokeOutcome> {
  return invokeRefreshSourcesManualWith(invoke, draft);
}
