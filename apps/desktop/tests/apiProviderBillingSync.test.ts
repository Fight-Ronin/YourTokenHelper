import {
  SYNC_API_PROVIDER_BILLING_COMMAND,
  buildSyncApiProviderBillingArgs,
  syncApiProviderBillingWith
} from "../src/commands/apiProviderBillingSync.js";
import type { TauriInvoke } from "../src/commands/refreshSourcesManualInvoker.js";

assert(
  SYNC_API_PROVIDER_BILLING_COMMAND === "sync_api_provider_billing",
  "API provider billing sync command name should match Tauri"
);

assertDeepEqual(
  buildSyncApiProviderBillingArgs({
    providerId: "openai_api_cost",
    endDayUtc: " 2026-06-14 ",
    startedAt: "2026-06-14T00:00:00Z"
  }),
  {
    provider_id: "openai_api_cost",
    end_day_utc: "2026-06-14",
    started_at: "2026-06-14T00:00:00Z"
  },
  "sync args should map UI names to backend boundary names"
);

assertDeepEqual(
  buildSyncApiProviderBillingArgs({
    providerId: "C:/Users/example/secret/provider" as never,
    endDayUtc: "2026-06-14"
  }),
  {
    error: {
      code: "invalid_api_provider_billing_sync_request",
      field: "provider_id",
      message: "Unknown API cost provider"
    }
  },
  "sync args should reject unknown provider ids"
);

assertDeepEqual(
  buildSyncApiProviderBillingArgs({
    providerId: "openai_api_cost",
    endDayUtc: "2026-6-14"
  }),
  {
    error: {
      code: "invalid_api_provider_billing_sync_request",
      field: "end_day_utc",
      message: "end_day_utc must be YYYY-MM-DD"
    }
  },
  "sync args should reject loose dates"
);

const successfulInvoke: TauriInvoke = async (command, payload) => {
  assert(command === SYNC_API_PROVIDER_BILLING_COMMAND, "sync should call the Tauri command");
  assertDeepEqual(payload, {
    args: {
      provider_id: "openai_api_cost",
      end_day_utc: "2026-06-14"
    }
  });
  return {
    sync_result: {
      source_kind: "openai_api_cost",
      source_id: "openai_api_cost:admin_api",
      status: "ready",
      confidence: "official",
      events_seen: 2,
      sync_run_id: 7
    },
    storage_summary: {
      schema_version: 1,
      generated_from: "backend.sources.openai_admin_commands",
      privacy: {
        synthetic: false,
        stores_prompt_content: false,
        stores_response_content: false,
        stores_tool_output: false
      },
      refresh_state: {
        last_attempt_at: null,
        last_success_at: null,
        last_status: "never_refreshed",
        successful_source_count: 0,
        attempted_source_count: 0,
        events_seen: 0
      },
      summary: {
        event_count: 0,
        totals: {
          input_tokens: 0,
          output_tokens: 0,
          cached_input_tokens: 0,
          reasoning_output_tokens: 0,
          total_tokens: 0
        },
        by_source: {},
        by_day: {},
        rolling_7d: {
          window_start: null,
          window_end: null,
          totals: {
            input_tokens: 0,
            output_tokens: 0,
            cached_input_tokens: 0,
            reasoning_output_tokens: 0,
            total_tokens: 0
          }
        }
      },
      cost_summary: {
        window_start: null,
        window_end: null,
        total_usd: null,
        by_source: {}
      },
      allowance_windows: [],
      source_states: []
    },
    provider_status: {
      provider_id: "openai_api_cost",
      status: "ready",
      adapter_verified: true,
      credential_configured: true
    },
    endpoint_statuses: {
      usage: "ready",
      costs: "ready"
    }
  } as never;
};
const syncOutcome = await syncApiProviderBillingWith(successfulInvoke, {
  providerId: "openai_api_cost",
  endDayUtc: "2026-06-14"
});
assert(syncOutcome.ok, "successful sync should return success");
assert(syncOutcome.providerStatus?.status === "ready", "provider status should be normalized");
assertDeepEqual(syncOutcome.result.endpoint_statuses, {
  usage: "ready",
  costs: "ready"
});
assert(
  !JSON.stringify(syncOutcome).includes("sk-admin-fixture-secret"),
  "sync outcome must not include key material"
);

const backendError = await syncApiProviderBillingWith(async () => ({
  error: {
    code: "api_provider_billing_sync_unavailable",
    field: "credential",
    message: "OpenAI API provider credential is not configured"
  }
} as never), {
  providerId: "openai_api_cost",
  endDayUtc: "2026-06-14"
});
assert(!backendError.ok, "backend error payload should return failed outcome");
assertDeepEqual(backendError.error, {
  error: {
    code: "api_provider_billing_sync_unavailable",
    field: "credential",
    message: "OpenAI API provider credential is not configured"
  }
});

const failingInvoke: TauriInvoke = async () => {
  throw new Error("C:/Users/example/secret/usage.sqlite sk-admin-fixture-secret");
};
const failedSync = await syncApiProviderBillingWith(failingInvoke, {
  providerId: "openai_api_cost",
  endDayUtc: "2026-06-14"
});
assert(!failedSync.ok, "thrown sync invoke should return redacted unavailable state");
assert(
  !JSON.stringify(failedSync).includes("C:/Users/example/secret"),
  "failed sync outcome must not echo thrown paths"
);
assert(
  !JSON.stringify(failedSync).includes("sk-admin-fixture-secret"),
  "failed sync outcome must not echo thrown keys"
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
