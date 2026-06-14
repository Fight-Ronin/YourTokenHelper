import type { RefreshCommandErrorPayload } from "../commands/refreshSourcesManualArgs.js";
import sourceRefreshErrorSampleJson from "../../src-tauri/source-refresh-error.sample.json" with {
  type: "json"
};

export const sourceRefreshErrorSample =
  sourceRefreshErrorSampleJson as RefreshCommandErrorPayload;
