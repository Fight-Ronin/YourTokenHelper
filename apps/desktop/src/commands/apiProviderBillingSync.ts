import { invoke } from "@tauri-apps/api/core";

import {
  apiProviderCredentialStatusFromPayload,
  type ApiProviderCredentialStatusPayload
} from "./apiProviderCredentials.js";
import { isApiCostProviderId, type ApiCostProviderStatus } from "../data/api-cost-providers.js";
import type { ApiCostSourceKind, RefreshStorageSummaryPayload } from "../types.js";
import type { CommandErrorPayload } from "./sourceRefreshSummary.js";
import type { TauriInvoke } from "./refreshSourcesManualInvoker.js";

export const SYNC_API_PROVIDER_BILLING_COMMAND = "sync_api_provider_billing" as const;

export type SyncApiProviderBillingDraft = {
  providerId: ApiCostSourceKind;
  endDayUtc: string;
  startedAt?: string;
};

export type SyncApiProviderBillingArgs = {
  provider_id: ApiCostSourceKind;
  end_day_utc: string;
  started_at?: string;
};

export const apiProviderEndpointConnectionStatuses = [
  "ready",
  "invalid_key",
  "permission_denied",
  "rate_limited",
  "unavailable"
] as const;

export type ApiProviderEndpointConnectionStatus =
  typeof apiProviderEndpointConnectionStatuses[number];

export type ApiProviderEndpointStatusesPayload = {
  usage: ApiProviderEndpointConnectionStatus;
  costs: ApiProviderEndpointConnectionStatus;
};

export type ApiProviderBillingSyncPayload = {
  sync_result: {
    source_kind: ApiCostSourceKind;
    source_id: string;
    status: string;
    confidence: string;
    usage_events_seen?: number;
    cost_records_seen?: number;
    events_seen: number;
    sync_run_id: number;
    message?: string;
  };
  storage_summary: RefreshStorageSummaryPayload;
  provider_status?: ApiProviderCredentialStatusPayload;
  endpoint_statuses?: ApiProviderEndpointStatusesPayload;
};

export type ApiProviderBillingSyncOutcome =
  | {
      ok: true;
      result: ApiProviderBillingSyncPayload;
      providerStatus?: ApiCostProviderStatus;
    }
  | {
      ok: false;
      error: CommandErrorPayload;
    };

export function buildSyncApiProviderBillingArgs(
  draft: SyncApiProviderBillingDraft
): SyncApiProviderBillingArgs | CommandErrorPayload {
  if (!isApiCostProviderId(draft.providerId)) {
    return invalidApiProviderBillingSyncArgs("provider_id", "Unknown API cost provider");
  }
  const endDayUtc = draft.endDayUtc.trim();
  if (!isStrictUtcDate(endDayUtc)) {
    return invalidApiProviderBillingSyncArgs("end_day_utc", "end_day_utc must be YYYY-MM-DD");
  }

  const args: SyncApiProviderBillingArgs = {
    provider_id: draft.providerId,
    end_day_utc: endDayUtc
  };
  const startedAt = draft.startedAt?.trim();
  if (startedAt) {
    args.started_at = startedAt;
  }
  return args;
}

export async function syncApiProviderBillingWith(
  tauriInvoke: TauriInvoke,
  draft: SyncApiProviderBillingDraft
): Promise<ApiProviderBillingSyncOutcome> {
  const args = buildSyncApiProviderBillingArgs(draft);
  if ("error" in args) {
    return { ok: false, error: args };
  }
  try {
    const result = await tauriInvoke<ApiProviderBillingSyncPayload | CommandErrorPayload>(
      SYNC_API_PROVIDER_BILLING_COMMAND,
      { args }
    );
    if (isApiProviderBillingSyncErrorPayload(result)) {
      return { ok: false, error: result };
    }
    return {
      ok: true,
      result,
      providerStatus: result.provider_status
        ? apiProviderCredentialStatusFromPayload(result.provider_status)
        : undefined
    };
  } catch {
    return apiProviderBillingSyncUnavailable();
  }
}

export function syncApiProviderBilling(draft: SyncApiProviderBillingDraft) {
  return syncApiProviderBillingWith(invoke, draft);
}

function invalidApiProviderBillingSyncArgs(
  field: "provider_id" | "end_day_utc",
  message: string
): CommandErrorPayload {
  return {
    error: {
      code: "invalid_api_provider_billing_sync_request",
      field,
      message
    }
  };
}

function apiProviderBillingSyncUnavailable(): ApiProviderBillingSyncOutcome {
  return {
    ok: false,
    error: {
      error: {
        code: "api_provider_billing_sync_unavailable",
        message: "API provider billing sync unavailable"
      }
    }
  };
}

function isApiProviderBillingSyncErrorPayload(
  result: ApiProviderBillingSyncPayload | CommandErrorPayload
): result is CommandErrorPayload {
  return "error" in result;
}

function isStrictUtcDate(value: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return false;
  }
  const date = new Date(`${value}T00:00:00.000Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}
