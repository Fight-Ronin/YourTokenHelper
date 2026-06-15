import {
  LOAD_API_PROVIDER_CREDENTIALS_COMMAND,
  REMOVE_API_PROVIDER_CREDENTIAL_COMMAND,
  SAVE_API_PROVIDER_CREDENTIAL_COMMAND,
  apiProviderCredentialStatusesFromPayload,
  buildRemoveApiProviderCredentialArgs,
  buildSaveApiProviderCredentialArgs,
  defaultApiProviderCredentialStatuses,
  loadApiProviderCredentialsWith,
  removeApiProviderCredentialWith,
  saveApiProviderCredentialWith
} from "../src/commands/apiProviderCredentials.js";
import type { TauriInvoke } from "../src/commands/refreshSourcesManualInvoker.js";

assert(
  LOAD_API_PROVIDER_CREDENTIALS_COMMAND === "load_api_provider_credentials",
  "load API provider credentials command name should match Tauri"
);
assert(
  SAVE_API_PROVIDER_CREDENTIAL_COMMAND === "save_api_provider_credential",
  "save API provider credential command name should match Tauri"
);
assert(
  REMOVE_API_PROVIDER_CREDENTIAL_COMMAND === "remove_api_provider_credential",
  "remove API provider credential command name should match Tauri"
);

assertDeepEqual(
  defaultApiProviderCredentialStatuses().map((status) => [status.providerId, status.status]),
  [
    ["openai_api_cost", "not_configured"],
    ["claude_api_cost", "needs_verified_adapter"],
    ["gemini_api_cost", "needs_verified_adapter"],
    ["deepseek_api_cost", "needs_verified_adapter"]
  ],
  "default API provider credential statuses should match provider contract"
);

assertDeepEqual(
  buildSaveApiProviderCredentialArgs({
    providerId: "openai_api_cost",
    apiKey: " sk-admin-fixture-secret "
  }),
  {
    provider_id: "openai_api_cost",
    api_key: "sk-admin-fixture-secret"
  },
  "save args should trim the transient key before invoking Tauri"
);
assertDeepEqual(
  buildSaveApiProviderCredentialArgs({
    providerId: "stored_but_assumed_ready" as never,
    apiKey: "sk-admin-fixture-secret"
  }),
  {
    error: {
      code: "invalid_api_provider_credential_request",
      field: "provider_id",
      message: "Unknown API cost provider"
    }
  },
  "save args should reject unknown provider ids"
);
assertDeepEqual(
  buildSaveApiProviderCredentialArgs({
    providerId: "openai_api_cost",
    apiKey: "  "
  }),
  {
    error: {
      code: "invalid_api_provider_credential_request",
      field: "api_key",
      message: "API provider credential is required"
    }
  },
  "save args should reject empty credentials"
);
assertDeepEqual(
  buildRemoveApiProviderCredentialArgs("C:/Users/example/secret/provider" as never),
  {
    error: {
      code: "invalid_api_provider_credential_request",
      field: "provider_id",
      message: "Unknown API cost provider"
    }
  },
  "remove args should reject unknown provider ids"
);

const loadedStatuses = apiProviderCredentialStatusesFromPayload({
  providers: [
    {
      provider_id: "openai_api_cost",
      status: "unavailable",
      adapter_verified: true,
      credential_configured: true
    },
    {
      provider_id: "claude_api_cost",
      status: "needs_verified_adapter",
      adapter_verified: false,
      credential_configured: true,
      message: "Provider billing adapter has not been verified."
    }
  ]
});
assertDeepEqual(
  loadedStatuses.map((status) => [status.providerId, status.status, status.credentialConfigured]),
  [
    ["openai_api_cost", "unavailable", true],
    ["claude_api_cost", "needs_verified_adapter", true],
    ["gemini_api_cost", "needs_verified_adapter", false],
    ["deepseek_api_cost", "needs_verified_adapter", false]
  ],
  "payload statuses should normalize missing providers through the shared defaults"
);

const successfulInvoke: TauriInvoke = async (command, payload) => {
  assert(command === SAVE_API_PROVIDER_CREDENTIAL_COMMAND, "save should call the save command");
  assertDeepEqual(payload, {
    args: {
      provider_id: "openai_api_cost",
      api_key: "sk-admin-fixture-secret"
    }
  });
  return {
    providers: [
      {
        provider_id: "openai_api_cost",
        status: "unavailable",
        adapter_verified: true,
        credential_configured: true
      }
    ]
  } as never;
};
const saveOutcome = await saveApiProviderCredentialWith(successfulInvoke, {
  providerId: "openai_api_cost",
  apiKey: "sk-admin-fixture-secret"
});
assert(saveOutcome.ok, "successful save invoke should return statuses");
assert(saveOutcome.statuses[0].credentialConfigured, "OpenAI credential should be configured after save");
assert(
  !JSON.stringify(saveOutcome).includes("sk-admin-fixture-secret"),
  "save outcome must not echo the transient key"
);

const loadOutcome = await loadApiProviderCredentialsWith(async (command) => {
  assert(command === LOAD_API_PROVIDER_CREDENTIALS_COMMAND, "load should call the load command");
  return { providers: [] } as never;
});
assert(loadOutcome.ok, "load invoke should return statuses");
assert(loadOutcome.statuses.length === 4, "load should complete missing provider statuses");

const removeOutcome = await removeApiProviderCredentialWith(async (command, payload) => {
  assert(command === REMOVE_API_PROVIDER_CREDENTIAL_COMMAND, "remove should call the remove command");
  assertDeepEqual(payload, { args: { provider_id: "openai_api_cost" } });
  return { providers: [] } as never;
}, "openai_api_cost");
assert(removeOutcome.ok, "remove invoke should return statuses");

const failingInvoke: TauriInvoke = async () => {
  throw new Error("C:/Users/example/secret/usage.sqlite sk-admin-fixture-secret");
};
const failedSave = await saveApiProviderCredentialWith(failingInvoke, {
  providerId: "openai_api_cost",
  apiKey: "sk-admin-fixture-secret"
});
assert(!failedSave.ok, "failed save invoke should return a redacted unavailable state");
assertDeepEqual(failedSave.error, {
  error: {
    code: "api_provider_credentials_unavailable",
    message: "API provider credentials unavailable"
  }
});
assert(
  !JSON.stringify(failedSave).includes("C:/Users/example/secret/usage.sqlite"),
  "failed save outcome must not echo thrown paths"
);
assert(
  !JSON.stringify(failedSave).includes("sk-admin-fixture-secret"),
  "failed save outcome must not echo thrown keys"
);

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function assertDeepEqual(actual: unknown, expected: unknown, message = "values should match") {
  const actualJson = JSON.stringify(actual);
  const expectedJson = JSON.stringify(expected);
  if (actualJson !== expectedJson) {
    throw new Error(`${message}: expected ${expectedJson}, got ${actualJson}`);
  }
}
