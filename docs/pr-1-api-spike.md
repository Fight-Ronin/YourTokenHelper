# PR 1: OpenAI Usage API Spike

## Goal

Validate the first real data path for YourTokenHelper before building the desktop shell.

This PR answers:

1. Can we fetch account/API organization usage with daily buckets?
2. Can we fetch dollar cost as a secondary estimate?
3. Can we fetch account allowance, remaining usage, and refresh/reset timing from an official API?

## Working Assumptions

- Personal/no-admin users are a primary target; organization/admin usage is an enhanced official data path.
- The spike validates OpenAI API organization/admin usage, not local Codex logs and not Claude usage.
- Daily and rolling 7-day views are the first-class product views.
- Monthly is lower priority.
- Cost is secondary context; consumed usage, remaining allowance, and refresh timing are primary.
- We must not use private dashboard endpoints or browser-scraped billing pages in this spike.

## Official API Surface To Validate

- Usage: `GET /v1/organization/usage/completions`
- Costs: `GET /v1/organization/costs`
- Account allowance/remaining/reset: not assumed available until verified from official API docs or live API behavior.

Standard personal/project API keys may not have access to the organization usage and costs endpoints. A permission-denied result is a valid spike finding and should feed product design.

If allowance data cannot be fetched from an official API, V1 should model it as one of:

- `manual`: user configured the allowance and refresh window.
- `derived`: app computed remaining allowance from a configured limit minus fetched usage.
- `unavailable`: app can show consumed usage but cannot state remaining usage.

The UI must label those states clearly.

## Data Safety

- Read credentials only from environment variables or local `.env` files.
- Prefer `OPENAI_ADMIN_KEY` when present; fall back to `OPENAI_API_KEY`.
- Never print or write plaintext API keys.
- Do not commit `.env`, live probe outputs, or raw API responses.
- Redact/hide stable identifiers such as `api_key_id`, `project_id`, and `user_id` in saved summaries.

## Probe Commands

Fixture mode, no network and no key required:

```powershell
python experiments/probes/openai_usage_probe.py --fixture experiments/fixtures/openai/sample_probe_response.json
```

Live mode, using `.env` or process environment:

```powershell
python experiments/probes/openai_usage_probe.py --live --days 7 --output .probe-output/openai-usage-summary.redacted.json
```

Optional explicit date range:

```powershell
python experiments/probes/openai_usage_probe.py --live --start-date 2026-06-07 --end-date 2026-06-14
```

Dates are interpreted as UTC calendar days. `end-date` is exclusive.

## Acceptance Criteria

- Fixture mode runs without a key.
- Live mode either returns a redacted usage/cost summary or records a safe permission/error state.
- Output contains daily buckets plus a rolling 7-day aggregate.
- Output distinguishes usage, cost, and allowance states.
- The spike leaves a clear recommendation for PR 2 mock UI data and PR 3 local storage schema.

## Expected Findings Template

After live validation, record:

- Key type used: `admin` / `project` / `unknown`.
- Usage status: available / permission denied / no data / error.
- Cost status: available / permission denied / no data / error.
- Allowance status: API-backed / manual needed / derived only / unavailable.
- Required grouping fields for V1: model, API key, project.
- Any missing data that affects daily or weekly views.

Current live findings are recorded in [PR 1 API Spike Findings](pr-1-api-spike-findings.md).
