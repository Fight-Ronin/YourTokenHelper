import {
  apiCostProviderIds,
  apiCostProviderStatusFor,
  apiCostProviderStatusLabel,
  isApiCostProviderId
} from "../src/data/api-cost-providers.js";

assertDeepEqual(
  apiCostProviderIds,
  ["openai_api_cost", "claude_api_cost", "gemini_api_cost", "deepseek_api_cost"],
  "API cost provider allowlist should include the supported provider brands"
);

assert(isApiCostProviderId("openai_api_cost"), "OpenAI API cost should be recognized");
assert(!isApiCostProviderId("C:/Users/example/.openai/admin-key.txt"), "local paths must not parse as providers");
assert(!isApiCostProviderId("stored_but_assumed_ready"), "unknown provider ids must not parse as providers");

assertDeepEqual(
  apiCostProviderStatusFor("openai_api_cost"),
  {
    providerId: "openai_api_cost",
    status: "not_configured",
    adapterVerified: true,
    credentialConfigured: false
  },
  "OpenAI should not be ready before a credential/import exists"
);

for (const providerId of ["claude_api_cost", "gemini_api_cost", "deepseek_api_cost"] as const) {
  assertDeepEqual(
    apiCostProviderStatusFor(providerId),
    {
      providerId,
      status: "needs_verified_adapter",
      adapterVerified: false,
      credentialConfigured: false,
      message: "Provider billing adapter has not been verified."
    },
    `${providerId} should stay explicit until an official billing adapter is verified`
  );
}

assertDeepEqual(
  apiCostProviderStatusFor("openai_api_cost", { credentialConfigured: true }),
  {
    providerId: "openai_api_cost",
    status: "unavailable",
    adapterVerified: true,
    credentialConfigured: true,
    message: "Provider credential has not been validated."
  },
  "configured credentials should still be unavailable until a probe/import reports a concrete state"
);

assert(
  apiCostProviderStatusLabel("needs_verified_adapter") === "Needs verified adapter",
  "provider status labels should use explicit adapter language"
);
assert(
  apiCostProviderStatusLabel("permission_denied") === "Permission denied",
  "permission failures should have an explicit label"
);
assertThrows(
  () => apiCostProviderStatusFor("stored_but_assumed_ready" as never),
  "Unknown API cost provider",
  "runtime provider validation should reject unknown provider ids"
);
assertThrows(
  () => apiCostProviderStatusFor("openai_api_cost", { status: "" as never }),
  "Unknown API cost provider status",
  "runtime status validation should reject empty status values"
);
assertThrows(
  () => apiCostProviderStatusLabel("" as never),
  "Unknown API cost provider status",
  "runtime status labels should reject empty status values"
);
assertThrows(
  () => apiCostProviderStatusFor("claude_api_cost", { status: "stored_but_assumed_ready" as never }),
  "Unknown API cost provider status",
  "runtime status validation should happen before adapter fallback"
);
assertThrows(
  () => apiCostProviderStatusFor("claude_api_cost", { credentialConfigured: true, status: "permission_denied" }),
  "Unverified API cost provider cannot accept concrete status",
  "unverified providers should not accept concrete permission states"
);
assertThrows(
  () => apiCostProviderStatusFor("openai_api_cost", { status: "needs_verified_adapter" }),
  "Verified API cost provider cannot be needs_verified_adapter",
  "verified providers should not report needs-verified-adapter"
);
assertThrows(
  () => apiCostProviderStatusFor("openai_api_cost", { status: "ready" }),
  "API cost provider status requires a configured credential",
  "ready status should require an explicit credential state"
);

const serialized = JSON.stringify(apiCostProviderStatusFor("deepseek_api_cost", { credentialConfigured: true }));
assert(!serialized.includes("C:/Users"), "provider status payload must not expose local paths");
assert(!serialized.includes("secret"), "provider status payload must not expose secret markers");
assert(!serialized.includes("admin-key"), "provider status payload must not expose key file names");

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function assertDeepEqual(actual: unknown, expected: unknown, message: string) {
  const actualJson = JSON.stringify(actual);
  const expectedJson = JSON.stringify(expected);
  if (actualJson !== expectedJson) {
    throw new Error(`${message}: expected ${expectedJson}, got ${actualJson}`);
  }
}

function assertThrows(action: () => void, expectedMessage: string, message: string) {
  try {
    action();
  } catch (error) {
    assert(error instanceof Error, `${message}: thrown value should be an Error`);
    assert(error.message === expectedMessage, `${message}: expected ${expectedMessage}, got ${error.message}`);
    return;
  }
  throw new Error(message);
}
