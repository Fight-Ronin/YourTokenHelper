import type { SourceRefreshSummaryPayload } from "../types.js";
import sourceRefreshSummarySampleJson from "../../src-tauri/source-refresh-summary.sample.json" with {
  type: "json"
};

export const sourceRefreshSummarySample =
  sourceRefreshSummarySampleJson as SourceRefreshSummaryPayload;
