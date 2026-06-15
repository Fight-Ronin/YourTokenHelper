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

Manual allowance persistence must accept only structured source, unit, numeric
limit/used/remaining values, and reset/window timestamps. It must not accept
paths, prompts, responses, raw transcripts, free-text notes, raw provider
payloads, or user-controlled source ids in UI-facing command payloads.

### Quota Research Refresh, 2026-06-15

Quota bars must be backed by an `allowance_windows` row with reliable limit data. The app must not infer remaining personal subscription usage from aggregate token events alone. Local token totals can support consumed-usage views, but they are not quota evidence by themselves.

| Source | Reliable usage data | Reliable limit/quota data | V1 decision |
| --- | --- | --- | --- |
| Codex | Local logs can expose aggregate token usage, and official surfaces describe usage/limit visibility outside the local JSONL parser path. | No observed durable local structured `allowance_windows` field is normalized from Codex JSONL refresh input. CLI/dashboard status is a future explicit import candidate, not an implicit local-log inference. | Keep refresh `allowance_windows` empty unless an official/local allowance field is captured or the user saves a manual window. Source Usage bars show usage share by default. |
| Claude Code | Local session history can expose token usage, and official cost/monitoring docs describe token and cost signals. | Official docs describe cost metrics as approximations in some contexts, and no stable local allowance contract is normalized by the current parser. | Treat synced events as consumed usage only. Quota progress needs a future explicit `/usage` or admin import after contract verification, or a manual/derived allowance window. |
| Cursor | Pricing docs say plans include model usage, on-demand usage can continue after included usage, and team admins can view usage in Admin Dashboard. Explicit usage export import is supported when the user provides a report root. | No verified personal local quota field or public personal quota API was found in official docs. | Support explicit usage export import for consumed usage. Quota progress needs an official/admin allowance field or manual/derived allowance. |
| Gemini CLI | Official quota concepts exist, and telemetry/export can expose token fields when configured. | Session stats or telemetry token fields are not yet a verified durable allowance window. Telemetry may include prompts/responses unless parsing is strictly whitelisted. | Support telemetry only through whitelist parsing. Quota progress needs a verified explicit stats/import contract or manual/derived allowance. |
| GitHub Copilot | Official REST endpoints provide enterprise/org usage metrics and reports for authorized callers. | Permissioned admin/enterprise metrics do not establish personal local token allowance or remaining quota. | Start with official report import for authorized org/enterprise users; personal mode remains manual/unavailable. |

Planning references:

- Codex pricing and usage limits: https://developers.openai.com/codex/pricing
- Claude Code costs and `/usage`: https://code.claude.com/docs/en/costs
- Cursor pricing and admin usage note: https://cursor.com/pricing
- Gemini CLI quotas: https://geminicli.com/docs/resources/quota-and-pricing/
- Gemini CLI telemetry fields: https://geminicli.com/docs/cli/telemetry/
- GitHub Copilot usage metrics reports: https://docs.github.com/en/rest/copilot/copilot-usage-metrics

Implementation rule for Source Usage bars:

- If a source has an API-backed, manual, or derived allowance window with enough limit and used data, show quota progress.
- If allowance is missing or unavailable, show the source's share of visible consumed usage without quota wording. UI copy should say `usage split` or equivalent, never `Limit unavailable` on Source Usage bars.
- Never create synthetic provider limits during refresh. Missing `allowance_windows` is a valid consumed-usage-only state.

### P1: API-Key Cost Sources

API cost is useful, but separate from personal subscription usage.

In the UI, API usage and cost should live on a secondary page/source. It should not block the primary Daily and Weekly local usage views.

The first live credential/sync implementation should be multi-provider at the
contract and UI layer. Provider credentials, status, and manual sync commands
should use an allowlisted provider id rather than OpenAI-specific command names:

- `openai_api_cost`.
- `claude_api_cost`.
- `gemini_api_cost`.
- `deepseek_api_cost`.

Provider-specific network logic should stay behind adapters. A provider must
remain `needs verified adapter` until its official billing API or export shape
has deterministic fixture coverage; the app must not imply that an unverified
provider is connected.

OpenAI is the first concrete adapter because its Admin usage/cost shape is
already represented by PR6 fixtures. OpenAI API cost support should use official
organization Administration APIs when available:

- Usage: `GET /v1/organization/usage/completions`.
- Costs: `GET /v1/organization/costs`.

If the user's key lacks `api.usage.read`, the app should show a permission/setup state, not a broken chart.

For other API cost providers, V1 can store provider credentials and show
setup/status rows, but manual sync must stay disabled with an explicit
needs-adapter state until the official source is verified. This keeps the
minimum product shape multi-brand without creating fake cost data or relying on
screen scraping.

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

- `source_kind`: `codex`, `claude_code`, `cursor`, `gemini_cli`, `github_copilot`, `openai_api_cost`, `claude_api_cost`, `gemini_api_cost`, `deepseek_api_cost`.
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
