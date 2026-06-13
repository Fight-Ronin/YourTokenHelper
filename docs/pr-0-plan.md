# PR 0 Plan: Product Foundation

Date: 2026-06-13

## Purpose

PR 0 is a docs-only kickoff PR. It should turn the research into a clear product and engineering plan before we scaffold the desktop app.

This PR should answer:

- What are we building first?
- What are we explicitly not building yet?
- What does "done" mean for v1?
- What should PR 1 implement?

## Working Assumptions

- The v1 user is an individual builder who wants to see daily and weekly Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, and API-key usage.
- The primary sources are personal coding-tool usage sources: Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot.
- API-key cost is a supported additional source when official APIs are available.
- Remaining available usage and refresh/reset timing are first-class product concepts, but they may require manual or derived allowance windows.
- An OpenAI Admin API key is required only for official OpenAI organization/API-key usage. A normal inference API key is not enough for that enhanced source.
- Daily and weekly monitoring are sufficient for v1. Monthly reporting is lower priority.
- The app should store aggregates, not prompts, responses, request bodies, or raw transcripts.

## Product Statement

YourTokenHelper is a lightweight cross-platform desktop app for viewing a specific user's Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, and API-key usage by day and by week.

The first version should help the user answer:

- How many tokens did I use today?
- How many tokens did I use this week?
- How much usage do I have left?
- When does my usage refresh?
- Which tool, model, workspace/project, session, or API key is responsible for most usage?
- What is the estimated dollar cost by API key or model?
- Is the data fresh and trustworthy?

## Non-Goals For V1

- Deep multi-agent workflow analytics.
- Realtime burn-rate monitoring.
- Session/thread drilldowns.
- Prompt or response inspection.
- Proxy mode, tracing, or LLM observability.
- Team roles, team dashboards, or shared workspaces.
- Billing reconciliation beyond OpenAI's exposed usage and cost buckets.
- Exact remaining-usage guarantees when allowance data is unavailable from the provider.

## V1 Scope

### Daily View

The daily view should show:

- Today's total tokens.
- Remaining available usage.
- Next refresh/reset time.
- Today's estimated dollar cost as a secondary metric.
- Request count.
- Token split: input, output, cached input, and reasoning output when available.
- Breakdown by tool/source.
- Breakdown by model.
- Breakdown by workspace/project/API key when available.
- Last sync time and sync status.

### Weekly View

The weekly view should show:

- Rolling 7-day total tokens.
- Remaining available usage.
- Next refresh/reset time.
- Rolling 7-day estimated dollar cost as a secondary metric.
- Daily trend across the last 7 days.
- Top tools/sources.
- Top models.
- Top workspaces/projects/API keys when available.
- Any missing or partial data warnings.

### Deferred Monthly View

Monthly reporting should be lower priority than Daily and Weekly. It can be considered after the local personal usage MVP is usable.

### Sources View

The sources view should show:

- Codex source status.
- Claude Code source status.
- Cursor source status.
- Gemini CLI source status.
- GitHub Copilot source status.
- OpenAI API cost source status.
- Last successful sync.
- Last sync error, if any.
- Whether usage and costs are both available.
- Whether allowance and refresh/reset data are fetched, manual, derived, or unavailable.

### Settings View

The settings view should support:

- Enable, disable, or rescan Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot sources.
- Add, replace, or remove OpenAI Admin API key for optional API cost sync.
- Configure manual allowance or refresh/reset time if no provider API is available.
- Manual sync.
- Timezone selection.
- Data retention period.
- Clear local cache.
- Export aggregate data.

## Data Source Plan

### Source Type Distinction

The product should distinguish:

- Local coding-tool usage: Codex, Claude Code, Cursor, Gemini CLI, and supported GitHub Copilot usage.
- API organization usage: OpenAI API usage and secondary dollar estimates when Admin API access is available.
- Allowance: remaining available usage and refresh/reset timing for each source or plan.

V1 should lead with local personal usage. If allowance data is manual or derived, the app should label it clearly and avoid presenting API cost data as remaining subscription usage.

### Primary: Local Coding Tool Sources

Support Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot as first-class source types.

PR 1b must verify:

- Local data paths on Windows, macOS, and Linux.
- Available timestamp, model, token, session, and workspace fields.
- Whether data can be parsed without retaining prompts or full transcripts.
- Whether any source exposes reset/remaining usage locally.
- Whether Cursor is parser-ready, export/manual-only, or blocked.
- Whether Gemini CLI requires explicit local telemetry output.
- Whether GitHub Copilot can use official metrics/report data or only manual fallback for personal users.

### Additional: OpenAI Admin Usage API

Use the official Administration APIs for API-key usage and secondary cost when available:

- Usage endpoint family: `/organization/usage/*`
- Costs endpoint: `/organization/costs`, used for secondary dollar estimates when available.

Important dimensions:

- `api_key_id`
- `model`
- `project_id`
- `user_id`

Important metrics:

- Input tokens.
- Output tokens.
- Cached input tokens.
- Reasoning output tokens, if returned.
- Request count.
- Cost amount, as a secondary estimate.

### Allowance And Refresh State

The app should model account-level usage availability:

- Usage consumed.
- Remaining available usage.
- Refresh/reset time.
- Window start and end.
- Data source and confidence.

PR 1b must verify whether this exists locally or officially for Codex, Claude Code, Cursor, Gemini CLI, or GitHub Copilot. If not, the product should support manual or derived estimates and label them clearly.

## Local Data Model

PR 0 should not implement the database yet, but the first implementation should start from these concepts:

### `sources`

- `id`
- `type`
- `display_name`
- `status`
- `last_synced_at`
- `last_error`

### `usage_buckets`

- `id`
- `source_id`
- `bucket_start`
- `bucket_end`
- `granularity`
- `api_key_id`
- `source_kind`
- `model`
- `workspace_id`
- `session_id`
- `project_id`
- `user_id`
- `input_tokens`
- `output_tokens`
- `cached_input_tokens`
- `reasoning_output_tokens`
- `request_count`

### `cost_buckets`

- `id`
- `source_id`
- `bucket_start`
- `bucket_end`
- `granularity`
- `api_key_id`
- `model`
- `project_id`
- `amount_usd`

### `allowance_windows`

- `id`
- `source_id`
- `window_start`
- `window_end`
- `usage_limit`
- `usage_consumed`
- `remaining_usage`
- `unit`
- `confidence`
- `data_source`

### `sync_runs`

- `id`
- `source_id`
- `started_at`
- `finished_at`
- `status`
- `rows_fetched`
- `error_code`
- `error_message`

## Security And Privacy Principles

- Store API keys in OS secure storage, not plaintext SQLite.
- Store only aggregate usage and cost records.
- Do not store prompts, responses, request payloads, or raw local transcripts by default.
- Make source status and sync errors visible.
- Allow users to delete all local app data.
- Avoid silently estimating or inventing missing costs.
- Avoid implying exact remaining usage when it is manual or derived.

## UX Principles

- Daily and Weekly are the main navigation items.
- The first screen should be the usable viewer, not a marketing page.
- Empty state should explain the exact next step: enable a local source, configure allowance, or connect optional API cost sync.
- Error state should say what failed and whether the user can fix it.
- Missing allowance or refresh data should be visible near usage status.
- Cost estimates should be visually secondary to usage and allowance.
- Avoid expert-only language such as index, bucket, or refresh job in the main UI.

## PR 0 Deliverables

This PR should include:

- This PR 0 plan.
- The market research summary.
- A short v1 PRD.
- A rough implementation roadmap.

This PR should not include:

- Tauri scaffolding.
- API client code.
- Database migrations.
- UI implementation.
- Installer or packaging work.

## Acceptance Criteria

PR 0 is done when:

- The product scope is clear enough to reject out-of-scope feature requests.
- The primary data sources are clearly defined as Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot.
- API-key cost support is clearly defined as an additional source.
- Allowance/remaining/refresh behavior is explicitly called out as something PR 1b must verify or support manually.
- Daily and weekly views have concrete fields.
- Security and privacy expectations are written down.
- PR 1 has a clear starting point.

## Proposed Follow-Up PRs

### PR 1: API Spike

Goal: validate the OpenAI Admin Usage/Costs API shape before building the app.

Deliverables:

- Small script or fixture-driven module for fetching daily usage and deriving weekly summaries.
- Notes on whether remaining usage and refresh/reset timing are available automatically.
- Captured sanitized sample responses or hand-written fixtures.
- Notes on pagination, grouping, date range limits, and error behavior.

### PR 2: Desktop Skeleton

Goal: create the cross-platform app shell.

Deliverables:

- Tauri v2 + React + TypeScript scaffold.
- App navigation: Daily, Weekly, Sources, Settings.
- Static mock data wired into the views.
- Basic design tokens and layout conventions.

### PR 3: Local Storage

Goal: add local aggregate persistence.

Deliverables:

- SQLite setup.
- Initial schema for sources, usage buckets, cost buckets, allowance windows, and sync runs.
- Repository/query layer for daily and weekly summaries.

### PR 4: OpenAI Source

Goal: connect real OpenAI Admin API data.

Deliverables:

- Secure key storage.
- Manual sync.
- Error states for invalid key, missing admin permissions, rate limits, and empty usage.
- Missing allowance/refresh states and manual fallback.
- Daily and weekly views backed by local synced data.

### PR 5: Polish And Export

Goal: make the app useful and trustworthy.

Deliverables:

- CSV/JSON export.
- Last sync and partial data indicators.
- Missing allowance/manual estimate indicators.
- Empty states.
- Settings for timezone and data clearing.
- Basic app packaging check on at least Windows.

## Open Questions

- Should v1 require an Admin API key, or should it also support manually imported CSV/JSON for users without admin access?
- Should local Codex logs be part of the first public release, or a later feature flag?
- How should secondary dollar estimates be presented when Usage API and Costs API differ in grouping availability?
- Can remaining available usage and refresh/reset timing be fetched from an official API for the target account type?
- If allowance data is unavailable through API, should V1 require manual allowance setup or ship in consumed-usage-only mode?
- What unit should account allowance use in the UI: tokens, credits, dollars, requests, or provider-specific usage units?
- Should Weekly mean rolling last 7 days, calendar week, or both?
- How much historical data should the first sync fetch by default: 14 days, 30 days, or 90 days?
- When should Monthly be promoted from lower-priority follow-up to a first-class view?
- Should API key names be fetched/displayed, or should the UI only show API key IDs until the user assigns aliases?
