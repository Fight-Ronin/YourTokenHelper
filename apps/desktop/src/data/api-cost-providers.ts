import type { ApiCostSourceKind } from "../types.js";

export const apiCostProviderIds = [
  "openai_api_cost",
  "claude_api_cost",
  "gemini_api_cost",
  "deepseek_api_cost"
] as const satisfies readonly ApiCostSourceKind[];

export const verifiedApiCostProviderIds = ["openai_api_cost"] as const satisfies readonly ApiCostSourceKind[];

export const apiCostProviderConnectionStatuses = [
  "not_configured",
  "needs_verified_adapter",
  "ready",
  "invalid_key",
  "permission_denied",
  "rate_limited",
  "unavailable"
] as const;

export type ApiCostProviderConnectionStatus = typeof apiCostProviderConnectionStatuses[number];

export type ApiCostProviderStatus = {
  providerId: ApiCostSourceKind;
  status: ApiCostProviderConnectionStatus;
  adapterVerified: boolean;
  credentialConfigured: boolean;
  message?: string;
};

const configuredCredentialStatuses = new Set<ApiCostProviderConnectionStatus>([
  "ready",
  "invalid_key",
  "permission_denied",
  "rate_limited",
  "unavailable"
]);
const providerStatusSet = new Set<string>(apiCostProviderConnectionStatuses);
const providerIdSet = new Set<string>(apiCostProviderIds);
const verifiedProviderIdSet = new Set<ApiCostSourceKind>(verifiedApiCostProviderIds);

export function isApiCostProviderId(value: string): value is ApiCostSourceKind {
  return providerIdSet.has(value);
}

export function apiCostProviderStatusFor(
  providerId: ApiCostSourceKind,
  options: {
    credentialConfigured?: boolean;
    status?: ApiCostProviderConnectionStatus;
  } = {}
): ApiCostProviderStatus {
  if (!isApiCostProviderId(providerId)) {
    throw new Error("Unknown API cost provider");
  }
  const credentialConfigured = options.credentialConfigured ?? false;
  const adapterVerified = verifiedProviderIdSet.has(providerId);
  if (options.status !== undefined && !providerStatusSet.has(options.status)) {
    throw new Error("Unknown API cost provider status");
  }

  if (!adapterVerified) {
    if (options.status !== undefined && options.status !== "needs_verified_adapter") {
      throw new Error("Unverified API cost provider cannot accept concrete status");
    }
    return {
      providerId,
      status: "needs_verified_adapter",
      adapterVerified: false,
      credentialConfigured,
      message: "Provider billing adapter has not been verified."
    };
  }

  if (options.status !== undefined) {
    if (options.status === "needs_verified_adapter") {
      throw new Error("Verified API cost provider cannot be needs_verified_adapter");
    }
    if (configuredCredentialStatuses.has(options.status) && !credentialConfigured) {
      throw new Error("API cost provider status requires a configured credential");
    }
    return {
      providerId,
      status: options.status,
      adapterVerified: true,
      credentialConfigured
    };
  }

  if (!credentialConfigured) {
    return {
      providerId,
      status: "not_configured",
      adapterVerified: true,
      credentialConfigured: false
    };
  }

  return {
    providerId,
    status: "unavailable",
    adapterVerified: true,
    credentialConfigured: true,
    message: "Provider credential has not been validated."
  };
}

export function apiCostProviderStatusLabel(status: ApiCostProviderConnectionStatus) {
  if (!providerStatusSet.has(status)) {
    throw new Error("Unknown API cost provider status");
  }
  const labels: Record<ApiCostProviderConnectionStatus, string> = {
    not_configured: "Not configured",
    needs_verified_adapter: "Needs verified adapter",
    ready: "Ready",
    invalid_key: "Invalid key",
    permission_denied: "Permission denied",
    rate_limited: "Rate limited",
    unavailable: "Unavailable"
  };
  return labels[status];
}
