import { sourceRefreshErrorSample } from "../data/source-refresh-error.sample.js";
import { sourceRefreshSummarySample } from "../data/source-refresh-summary.sample.js";
import type { RefreshStorageSummaryPayload, SourceRefreshSummaryPayload } from "../types.js";
import {
  buildRefreshSourcesManualArgs,
  type RefreshCommandErrorPayload,
  type RefreshSourcesManualArgs
} from "./refreshSourcesManualArgs.js";

export {
  buildRefreshSourcesManualArgs,
  manualRefreshEndDayUtc,
  type RefreshCommandErrorPayload,
  type RefreshSourcesManualArgs,
  type RefreshSourcesManualArgsBuildResult,
  type RefreshSourcesManualDraft
} from "./refreshSourcesManualArgs.js";

export const SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND =
  "source_refresh_summary_sample" as const;
export const REFRESH_SOURCES_MANUAL_COMMAND = "refresh_sources_manual" as const;
export const LOAD_STORAGE_SUMMARY_COMMAND = "load_storage_summary" as const;

export type RefreshSourcesManualResult =
  | SourceRefreshSummaryPayload
  | RefreshCommandErrorPayload;

export type CommandErrorPayload = {
  error: {
    code: string;
    message: string;
    field?: string;
  };
};

export type LoadStorageSummaryArgs = {
  end_day_utc: string;
};

export type LoadStorageSummaryResult =
  | RefreshStorageSummaryPayload
  | CommandErrorPayload;

export type SourceRefreshSummarySampleCommand = {
  name: typeof SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND;
  result: SourceRefreshSummaryPayload;
};

export type RefreshSourcesManualCommand = {
  name: typeof REFRESH_SOURCES_MANUAL_COMMAND;
  args: RefreshSourcesManualArgs;
  result: RefreshSourcesManualResult;
};

export type RefreshSourcesManualErrorCommand = {
  name: typeof REFRESH_SOURCES_MANUAL_COMMAND;
  result: RefreshCommandErrorPayload;
};

export type LoadStorageSummaryCommand = {
  name: typeof LOAD_STORAGE_SUMMARY_COMMAND;
  args: LoadStorageSummaryArgs;
  result: LoadStorageSummaryResult;
};

export function isRefreshCommandErrorPayload(
  result: RefreshSourcesManualResult | LoadStorageSummaryResult
): result is CommandErrorPayload {
  return "error" in result;
}

export function isSourceRefreshSummaryPayload(
  result: RefreshSourcesManualResult
): result is SourceRefreshSummaryPayload {
  return !isRefreshCommandErrorPayload(result);
}

export function isStorageSummaryPayload(
  result: LoadStorageSummaryResult
): result is RefreshStorageSummaryPayload {
  return !isRefreshCommandErrorPayload(result);
}

export const sourceRefreshSummarySampleCommandContract: SourceRefreshSummarySampleCommand =
  {
    name: SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND,
    result: sourceRefreshSummarySample
  };

const refreshSourcesManualCommandContractArgs = buildRefreshSourcesManualArgs({
  endDayUtc: "2026-06-14"
});

export const refreshSourcesManualCommandContract: RefreshSourcesManualCommand = {
  name: REFRESH_SOURCES_MANUAL_COMMAND,
  args: refreshSourcesManualCommandContractArgs.ok
    ? refreshSourcesManualCommandContractArgs.args
    : { end_day_utc: "2026-06-14" },
  result: sourceRefreshSummarySample
};

export const refreshSourcesManualErrorCommandContract: RefreshSourcesManualErrorCommand =
  {
    name: REFRESH_SOURCES_MANUAL_COMMAND,
    result: sourceRefreshErrorSample
  };

export const loadStorageSummaryCommandContract: LoadStorageSummaryCommand = {
  name: LOAD_STORAGE_SUMMARY_COMMAND,
  args: { end_day_utc: "2026-06-14" },
  result: sourceRefreshSummarySample.storage_summary
};
