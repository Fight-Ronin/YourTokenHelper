# Source Strategy V1

Date: 2026-06-14

## Product Direction

YourTokenHelper V1 is a small personal desktop utility for understanding coding-agent usage across:

1. Codex.
2. Claude Code.
3. Cursor.
4. Gemini CLI.
5. GitHub Copilot.
6. API-key cost sources, when official usage/cost APIs are available.

The app should help one user answer:

- How much did I use today?
- How much did I use this week?
- Which tool/model/session drove the usage?
- How much allowance do I appear to have left?
- When does the relevant usage window refresh?
- Which numbers are official, local, estimated, manual, or unavailable?

## Source Priority

### P0: Local Coding Tool Usage

These sources are the main V1 value.

| Source | V1 goal | Expected access | Confidence |
| --- | --- | --- | --- |
| Codex | Daily/weekly tokens, model, session/thread, estimated credits/cost | Local logs or local app state | Spike required |
| Claude Code | Daily/weekly tokens, plan usage approximation, model/session breakdown where present | Local session history and/or existing local usage command output | High, but field shape still needs spike |
| Cursor | Daily/weekly usage where locally observable, plus context/report data if accessible | Local app data, exported context reports, or manual/account dashboard fallback | Spike required |
| Gemini CLI | Daily/weekly tokens, model, local telemetry/export usage where configured | `.gemini` telemetry/export data; may require user opt-in | Spike required |
| GitHub Copilot | Daily/weekly official usage where available, plus personal manual fallback | Official usage metrics/report APIs for org/enterprise; local detection only for personal mode | Permission constrained |

V1 should read only the minimum needed for aggregate usage. It should not store prompts, tool output, code snippets, or full chat transcripts.

Additional programming-agent source decisions are tracked in `docs/programming-agent-source-candidates.md`. Only Gemini CLI and GitHub Copilot are added; other agents are out of scope.

### P1: Manual Allowance Windows

Manual allowance is required because personal subscription remaining usage may not have a public API.

The user should be able to configure per-source allowance windows:

- Source: Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, or API.
- Window type: daily, rolling 7 days, weekly, or custom.
- Limit unit: tokens, credits, requests, dollars, or provider-specific usage units.
- Refresh/reset time.

Derived remaining usage should always be labeled as an estimate.

### P1: API-Key Cost Source

API cost is useful, but separate from personal subscription usage.

In the UI, API usage and cost should live on a secondary page/source. It should not block the primary Daily and Weekly local usage views.

OpenAI API cost support should use official organization Administration APIs when available:

- Usage: `GET /v1/organization/usage/completions`.
- Costs: `GET /v1/organization/costs`.

If the user's key lacks `api.usage.read`, the app should show a permission/setup state, not a broken chart.

### Explicit Non-Source

V1 should not log into personal web accounts inside a WebView to scrape private/internal endpoints.

Reasons:

- Fragile and likely to break.
- Risky for credentials and cookies.
- Hard to keep open-source and trustworthy.
- Ambiguous terms-of-service posture.

## Unified Data Contract

Every parser or API connector should normalize data into aggregate events.

### Usage Event

Required:

- `source_kind`: `codex`, `claude_code`, `cursor`, `gemini_cli`, `github_copilot`, `openai_api_cost`.
- `source_id`: stable local identifier.
- `started_at`.
- `ended_at`, if available.
- `model`, if available.
- `input_tokens`, if available.
- `output_tokens`, if available.
- `total_tokens`.
- `confidence`: `official`, `local_exact`, `local_estimated`, `manual`, `unavailable`.

Optional:

- `cached_input_tokens`.
- `reasoning_output_tokens`.
- `requests`.
- `session_id`.
- `workspace_id`.
- `project_id`.
- `api_key_id`.
- `cost_usd`.
- `usage_credits`.
- `raw_source_ref`, stored as a local path/hash pointer, not raw prompt content.

### Allowance Window

Required:

- `source_kind`.
- `window_start`.
- `window_end`.
- `limit_value`.
- `limit_unit`.
- `consumed_value`.
- `remaining_value`.
- `confidence`: `official`, `manual`, `derived`, `unavailable`.

## First Implementation Plan

### PR 1b: Local Source Discovery Spike

Goal: prove which local sources are readable without storing sensitive content.

Scope:

- Detect likely Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot local data directories.
- Count candidate session/history files.
- Sample only schema keys and token fields, not prompt text.
- Emit a redacted source capability report.
- Document each source as `ready`, `needs-parser`, `manual-only`, `permission-denied`, or `not-found`.

Non-goals:

- No desktop UI.
- No persistent database.
- No full transcript storage.
- No personal account WebView login.

### PR 2: Parser Contract And Fixtures

Goal: create deterministic fixtures and parser tests for the sources proven in PR 1b.

Priority order:

1. Claude Code, because official docs expose local `/usage` behavior and day/week usage concepts.
2. Codex, because existing tools have shown local aggregate parsing is viable.
3. Cursor, because local data shape is less certain and may require a best-effort or manual/export path.
4. Gemini CLI, because official telemetry exposes token fields but prompt/response text must be excluded.
5. GitHub Copilot, because official metrics/report access is permission constrained and personal local usage is not assumed.
6. OpenAI API cost, because it requires Admin API access and is separate from personal coding-tool subscriptions.

Cursor can keep parser interface and synthetic fixture coverage before real parser readiness. On the current development machine, Cursor local data is `not-found`, so real Cursor parsing should wait for observed data or an official export shape.

Gemini CLI can keep parser interface and synthetic telemetry fixture coverage before real parser readiness. On the current development machine, Gemini CLI local data is `not-found`.

GitHub Copilot can keep official metrics/report fixture coverage. On the current development machine, one local Copilot candidate file exists, but no token fields were observed, so personal local parsing is not ready.

### PR 3: Desktop Mock UI

Goal: Daily and Weekly viewer over mock normalized events.

Must show:

- Tool split: Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, API.
- Today usage.
- Rolling 7-day usage.
- Remaining estimate and next reset.
- Cost/credit estimate.
- Data confidence labels.

## Open Questions

- Where exactly does Codex store usage-bearing session data on Windows, macOS, and Linux?
- Does Cursor expose enough local token usage for personal users, or only team/admin dashboards and context reports?
- Should Gemini CLI support require explicitly configured local telemetry output?
- Should GitHub Copilot support start with official reports only, leaving personal local mode as manual?
- Should Cursor V1 be local parser, user export/import, or manual allowance tracking until a stable source is confirmed?
- Should allowance defaults be provider-specific templates, or fully manual in V1?
- Which pricing/rate cards can be bundled safely, and which should be user-configured?
