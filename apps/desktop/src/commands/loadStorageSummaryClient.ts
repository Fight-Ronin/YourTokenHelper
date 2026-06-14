import { invoke } from "@tauri-apps/api/core";

import {
  LOAD_STORAGE_SUMMARY_COMMAND,
  type LoadStorageSummaryArgs,
  type LoadStorageSummaryResult
} from "./sourceRefreshSummary.js";
import { loadStartupStorageSummaryWith } from "./loadStorageSummaryStartup.js";

export {
  loadStartupStorageSummaryWith,
  type StartupStorageSummaryOutcome
} from "./loadStorageSummaryStartup.js";

export function invokeLoadStorageSummary(
  args: LoadStorageSummaryArgs
): Promise<LoadStorageSummaryResult> {
  return invoke<LoadStorageSummaryResult>(LOAD_STORAGE_SUMMARY_COMMAND, { args });
}

export function loadStartupStorageSummary(
  args: LoadStorageSummaryArgs
): ReturnType<typeof loadStartupStorageSummaryWith> {
  return loadStartupStorageSummaryWith(() => invokeLoadStorageSummary(args));
}
