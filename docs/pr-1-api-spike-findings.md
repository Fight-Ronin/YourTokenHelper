# PR 1 API Spike Findings

Last updated: 2026-06-14

## What Ran

Fixture smoke test:

```powershell
python experiments/probes/openai_usage_probe.py --fixture experiments/fixtures/openai/sample_probe_response.json --output .probe-output/fixture-summary.redacted.json
```

Live permission probe:

```powershell
python experiments/probes/openai_usage_probe.py --live --days 7 --output .probe-output/openai-live-summary.redacted.json
```

The live output is intentionally ignored by git because it may contain account-specific aggregate metadata.

## Current Result

- Key source: `OPENAI_API_KEY`
- Usage endpoint: permission denied
- Cost endpoint: permission denied
- OpenAI error: missing `api.usage.read`
- Allowance/remaining/reset: not probed through private endpoints

## Interpretation

The normal API key in `.env` is not enough for organization usage/cost reporting. The next live validation needs an admin or restricted API key that includes `api.usage.read`.

This is useful product information:

- V1 must have a clear credential diagnostics state.
- The app should not simply say "no data" when the key lacks usage scope.
- Usage/cost sync setup should explain that generation keys and usage-reporting keys may be different.

## Personal Account Constraint

The current development account is a personal account with a standard API key, not an organization/admin setup. V1 cannot assume users can create or provide an Admin API key.

Product implication:

- Personal/no-admin mode should be a first-class path, not an error-only dead end.
- Official organization usage/cost sync becomes an enhanced capability for users who have Admin API access.
- For personal users, V1 should still support manual or derived allowance tracking and clear setup diagnostics.
- If no official usage API is available for the key, the app should explain the limitation and avoid implying that account remaining usage is known.

## Product Decision So Far

Keep these states in the V1 data model:

- `usage.available`
- `usage.permission_denied`
- `costs.available`
- `costs.permission_denied`
- `allowance.api_backed`
- `allowance.manual`
- `allowance.derived`
- `allowance.unavailable`

For the UI, permission-denied is a setup problem, not an empty chart.

## Next Validation

If an Admin API key becomes available later, rerun:

```powershell
python experiments/probes/openai_usage_probe.py --live --days 7 --output .probe-output/openai-live-summary.redacted.json
```

Expected next question:

- Does the usage endpoint return daily completion buckets grouped by API key, project, and model?
- Does the costs endpoint return daily USD buckets grouped by project and line item?
- Is there any official API-backed source for allowance, remaining usage, and reset timing?
