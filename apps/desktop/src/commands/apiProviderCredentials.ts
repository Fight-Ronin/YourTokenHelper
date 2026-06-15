import { invoke } from "@tauri-apps/api/core";

import {
  apiCostProviderIds,
  apiCostProviderStatusFor,
  isApiCostProviderId,
  type ApiCostProviderStatus
} from "../data/api-cost-providers.js";
import type { ApiCostSourceKind } from "../types.js";
import type { CommandErrorPayload } from "./sourceRefreshSummary.js";
import type { TauriInvoke } from "./refreshSourcesManualInvoker.js";

export const LOAD_API_PROVIDER_CREDENTIALS_COMMAND = "load_api_provider_credentials" as const;
export const SAVE_API_PROVIDER_CREDENTIAL_COMMAND = "save_api_provider_credential" as const;
export const REMOVE_API_PROVIDER_CREDENTIAL_COMMAND = "remove_api_provider_credential" as const;

export type ApiProviderCredentialStatusPayload = {
  provider_id: ApiCostSourceKind;
  status: ApiCostProviderStatus["status"];
  adapter_verified: boolean;
  credential_configured: boolean;
  message?: string;
};

export type ApiProviderCredentialsPayload = {
  providers: ApiProviderCredentialStatusPayload[];
};

export type SaveApiProviderCredentialDraft = {
  providerId: ApiCostSourceKind;
  apiKey: string;
};

export type SaveApiProviderCredentialArgs = {
  provider_id: ApiCostSourceKind;
  api_key: string;
};

export type RemoveApiProviderCredentialArgs = {
  provider_id: ApiCostSourceKind;
};

export type ApiProviderCredentialOutcome =
  | {
      ok: true;
      statuses: ApiCostProviderStatus[];
    }
  | {
      ok: false;
      error: CommandErrorPayload;
    };

export function defaultApiProviderCredentialStatuses(): ApiCostProviderStatus[] {
  return apiCostProviderIds.map((providerId) => apiCostProviderStatusFor(providerId));
}

export function apiProviderCredentialStatusesFromPayload(
  payload: ApiProviderCredentialsPayload
): ApiCostProviderStatus[] {
  return apiCostProviderIds.map((providerId) => {
    const provider = payload.providers.find((item) => item.provider_id === providerId);
    if (!provider) {
      return apiCostProviderStatusFor(providerId);
    }
    return apiProviderCredentialStatusFromPayload(provider);
  });
}

export function apiProviderCredentialStatusFromPayload(
  provider: ApiProviderCredentialStatusPayload
): ApiCostProviderStatus {
  return apiCostProviderStatusFor(provider.provider_id, {
    credentialConfigured: provider.credential_configured,
    status: provider.status
  });
}

export function buildSaveApiProviderCredentialArgs(
  draft: SaveApiProviderCredentialDraft
): SaveApiProviderCredentialArgs | CommandErrorPayload {
  if (!isApiCostProviderId(draft.providerId)) {
    return invalidApiProviderCredentialArgs("provider_id", "Unknown API cost provider");
  }
  const apiKey = draft.apiKey.trim();
  if (!apiKey) {
    return invalidApiProviderCredentialArgs("api_key", "API provider credential is required");
  }
  return {
    provider_id: draft.providerId,
    api_key: apiKey
  };
}

export function buildRemoveApiProviderCredentialArgs(
  providerId: ApiCostSourceKind
): RemoveApiProviderCredentialArgs | CommandErrorPayload {
  if (!isApiCostProviderId(providerId)) {
    return invalidApiProviderCredentialArgs("provider_id", "Unknown API cost provider");
  }
  return { provider_id: providerId };
}

export async function loadApiProviderCredentialsWith(
  tauriInvoke: TauriInvoke
): Promise<ApiProviderCredentialOutcome> {
  try {
    const payload = await tauriInvoke<ApiProviderCredentialsPayload>(LOAD_API_PROVIDER_CREDENTIALS_COMMAND);
    return {
      ok: true,
      statuses: apiProviderCredentialStatusesFromPayload(payload)
    };
  } catch {
    return apiProviderCredentialUnavailable();
  }
}

export async function saveApiProviderCredentialWith(
  tauriInvoke: TauriInvoke,
  draft: SaveApiProviderCredentialDraft
): Promise<ApiProviderCredentialOutcome> {
  const args = buildSaveApiProviderCredentialArgs(draft);
  if ("error" in args) {
    return { ok: false, error: args };
  }
  try {
    const payload = await tauriInvoke<ApiProviderCredentialsPayload>(SAVE_API_PROVIDER_CREDENTIAL_COMMAND, {
      args
    });
    return {
      ok: true,
      statuses: apiProviderCredentialStatusesFromPayload(payload)
    };
  } catch {
    return apiProviderCredentialUnavailable();
  }
}

export async function removeApiProviderCredentialWith(
  tauriInvoke: TauriInvoke,
  providerId: ApiCostSourceKind
): Promise<ApiProviderCredentialOutcome> {
  const args = buildRemoveApiProviderCredentialArgs(providerId);
  if ("error" in args) {
    return { ok: false, error: args };
  }
  try {
    const payload = await tauriInvoke<ApiProviderCredentialsPayload>(REMOVE_API_PROVIDER_CREDENTIAL_COMMAND, {
      args
    });
    return {
      ok: true,
      statuses: apiProviderCredentialStatusesFromPayload(payload)
    };
  } catch {
    return apiProviderCredentialUnavailable();
  }
}

export function loadApiProviderCredentials() {
  return loadApiProviderCredentialsWith(invoke);
}

export function saveApiProviderCredential(draft: SaveApiProviderCredentialDraft) {
  return saveApiProviderCredentialWith(invoke, draft);
}

export function removeApiProviderCredential(providerId: ApiCostSourceKind) {
  return removeApiProviderCredentialWith(invoke, providerId);
}

function invalidApiProviderCredentialArgs(
  field: "provider_id" | "api_key",
  message: string
): CommandErrorPayload {
  return {
    error: {
      code: "invalid_api_provider_credential_request",
      field,
      message
    }
  };
}

function apiProviderCredentialUnavailable(): ApiProviderCredentialOutcome {
  return {
    ok: false,
    error: {
      error: {
        code: "api_provider_credentials_unavailable",
        message: "API provider credentials unavailable"
      }
    }
  };
}
