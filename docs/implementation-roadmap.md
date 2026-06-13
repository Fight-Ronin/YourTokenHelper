# Implementation Roadmap

Date: 2026-06-13

## Purpose

This roadmap breaks the V1 PRD into small, reviewable pull requests.

The goal is to avoid jumping straight into a desktop scaffold before the data source is understood. Each PR should have a narrow outcome, a clear verification step, and an explicit non-goal list.

## Current Product Direction

V1 is a Daily and Weekly personal coding-tool usage viewer.

- Daily means today's usage in the user's selected timezone.
- Weekly means rolling last 7 days for the first implementation.
- Usage consumed, remaining available usage, and refresh/reset timing are the primary product signals.
- Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot are the primary source targets.
- API-key dollar cost is a supported secondary source, not the primary product signal.
- Monthly is a lower-priority follow-up, not a first-class V1 view.
- Local personal usage is the default path; official API sync is an enhancement when available.
- Personal/no-admin users are the default target.
- The next spike must verify Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot source availability before committing to real parsers.
- The API spike already showed that a standard OpenAI API key lacks `api.usage.read`; official OpenAI usage/cost sync needs Admin API access.

## PR 0: Product Foundation

Status: in progress.

### Scope

- Market research summary.
- PR 0 plan.
- V1 PRD.
- Implementation roadmap.

### Verification

- Docs clearly say Daily and Weekly are V1 priorities.
- Docs clearly say Monthly is lower priority.
- Docs clearly say Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot are primary V1 sources.
- Docs clearly say API-key cost is supported as a separate source.
- Docs clearly say official OpenAI organization/API-key usage requires the OpenAI Administration APIs.
- Docs clearly say personal/no-admin users may need manual or derived allowance tracking.
- Docs clearly say remaining usage and refresh/reset timing are first-class product goals but require API verification or manual fallback.
- Docs do not include app scaffolding, API clients, migrations, or UI code.

### Non-Goals

- No Tauri scaffold.
- No OpenAI API calls.
- No SQLite schema.
- No key storage implementation.

## PR 1: OpenAI API Cost Spike

Status: complete enough for planning.

### Goal

Validate OpenAI Administration Usage, Costs, and allowance/refresh behavior for the optional API-key cost source.

### Scope

- Create a small spike script or minimal module that can call usage and costs endpoints.
- Support a local environment variable or temporary config for an Admin API key.
- Fetch a short time range suitable for Daily and Weekly summaries.
- Try grouping by `api_key_id`, `model`, and `project_id`.
- Investigate whether remaining available usage, allowance window, and refresh/reset timing are available through an official endpoint for the target account type.
- Document whether the validated account type is API organization usage, account/plan allowance, or both.
- Document personal/no-admin behavior when a standard API key lacks `api.usage.read`.
- Save sanitized example responses or hand-written fixtures under a test/fixtures location.
- Document the observed API shape and limitations.

### Verification

- A developer can run the spike against an Admin API key.
- The spike can fetch at least one usage response or a clear no-usage response.
- The spike can fetch costs or capture the exact failure/permission behavior.
- The spike documents whether allowance/remaining/refresh data is API-backed, unavailable, or requires another source.
- The spike records whether personal/no-admin mode must be supported for the intended V1 user.
- The notes explain pagination, time bucket boundaries, grouping support, and error states.

### Non-Goals

- No desktop UI.
- No secure key storage.
- No long-lived local database.
- No production sync worker.
- No Local Codex parser.

### Risks To Resolve

- Whether costs can be grouped at the same dimensions as usage.
- Whether API key names are available or only API key IDs.
- Whether model-level costs are available directly or must be shown as usage-only.
- Whether the API returns reasoning output tokens consistently.
- Whether account allowance uses tokens, credits, dollars, requests, or another unit.
- Whether reset/refresh time is fixed, rolling, plan-specific, or unavailable.

## PR 1b: Local Source Discovery Spike

### Goal

Validate Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot usage sources before committing to parsers or the desktop schema.

### Scope

- Detect likely local data directories or source availability for Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot on the current machine.
- Count candidate session/history files without storing prompt text.
- Sample schema keys and token-related fields only.
- Identify which sources can produce daily and weekly aggregate usage.
- Identify whether any source exposes allowance, remaining usage, or reset timing locally.
- Emit a redacted capability report.
- Update fixtures for each source that is ready enough for parser work.

### Verification

- A developer can run the discovery spike without network access.
- The report says `ready`, `needs-parser`, `manual-only`, `permission-denied`, or `not-found` for each source.
- No prompt, tool output, code snippet, or full transcript is written to the repo.
- The report identifies minimum fields available for daily/weekly aggregation.
- Cursor is explicitly marked based on observed local data, not assumed.

### Non-Goals

- No desktop UI.
- No persistent SQLite database.
- No full transcript parsing.
- No personal account WebView login.
- No API billing sync.

### Risks To Resolve

- Cursor local data may not contain stable token counts.
- Gemini CLI usage may require explicit local telemetry output.
- GitHub Copilot personal local data may not contain token counts; official metrics/report access may require organization or enterprise permissions.
- Codex and Claude Code may differ by surface: CLI, desktop, VS Code, web, or cloud sessions.
- Local data may cover only this machine, not browser/cloud usage.
- Some local stores may include sensitive prompt content, so parsers must be selective.

## PR 2: Parser Contract And Fixtures

Status: in progress.

### Goal

Create the normalized usage-event contract and deterministic fixtures for local sources.

### Scope

- Define normalized usage events and allowance windows.
- Add parser fixtures for Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot where PR 1b confirms field availability or official/report shape.
- Add API cost fixtures from the existing OpenAI probe.
- Add unit tests for daily and rolling 7-day aggregation.
- Ensure parser outputs do not include prompt text or full transcripts.
- Keep Cursor and Gemini CLI represented in the contract even if local data is not detected on the current machine.
- Keep GitHub Copilot represented through official metrics/report fixture coverage and personal manual fallback.

### Verification

- Fixture tests pass.
- Daily and Weekly aggregates are derived from normalized events.
- Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, and API cost can be represented by the same contract.
- Missing cost, missing allowance, and source-specific confidence labels are preserved.
- Cursor parser readiness is not implied unless real local Cursor data or an official export shape is observed.
- Gemini CLI parser readiness is not implied unless local telemetry/export data is observed.
- GitHub Copilot personal local parser readiness is not implied unless token fields are observed.

### Non-Goals

- No desktop UI.
- No real local user data committed.
- No persistent storage beyond fixtures.
- No live OpenAI API calls.
- No Monthly view.

## PR 3: Desktop Shell With Mock Data

### Goal

Create the cross-platform desktop shell and validate the Daily/Weekly UX with mock data.

### Scope

- Scaffold Tauri v2, React, and TypeScript.
- Add navigation for Daily, Weekly, Sources, and Settings.
- Add mock aggregate data for Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, API cost, allowance, and refresh/reset time.
- Build the first layout for the Daily view.
- Build the first layout for the Weekly view.
- Add first-launch and no-source empty states.
- Use `docs/interface-design-v1.md` as the visual and interaction direction for the mock UI.

### Verification

- App runs locally in development mode.
- Daily and Weekly screens render from mock data.
- Usage consumed, remaining usage, and refresh/reset time are visible as primary signals.
- Dollar cost appears as a secondary estimate.
- Sources and Settings routes exist, even if mostly placeholder.
- The first screen is a usable viewer or setup state, not a marketing page.

### Non-Goals

- No real OpenAI API calls.
- No persistent storage beyond static mock data.
- No packaging pipeline.
- No live local parser integration.
- No Monthly view.

### Design Checks

- Dashboard layout should be compact and utility-focused.
- Cards should be used only for metrics or repeated items.
- Daily and Weekly should be reachable from primary navigation.
- Error and empty states should be visible in mock mode.

## PR 4: Local Storage

### Goal

Persist aggregate source, usage, cost, and sync metadata locally.

### Scope

- Add SQLite setup.
- Add migrations for:
  - `sources`
  - `usage_buckets`
  - `cost_buckets`
  - `allowance_windows`
  - `sync_runs`
- Add query functions for:
  - Today's summary.
  - Rolling 7-day summary.
  - Daily trend for the last 7 days.
  - Breakdowns by API key, model, and project.
- Replace static mock data with seeded local fixture data where useful.

### Verification

- Migrations run cleanly on a fresh app data directory.
- Query tests cover Daily and Weekly summaries.
- Weekly totals are derived from daily buckets.
- Remaining usage can be represented as API-backed, manual, derived, or unavailable.
- Clearing the local cache removes aggregate data without touching settings.

### Non-Goals

- No real OpenAI sync yet.
- No local source sync yet.
- No OS keychain integration yet unless needed for schema testing.
- No Monthly view.
- No prompt or raw request storage.

### Risks To Resolve

- How to represent partial cost data without corrupting totals.
- How to represent missing allowance data without implying exact remaining usage.
- Whether costs and usage should share a common bucket table or remain separate.
- How to handle timezone changes after data has been synced.

## PR 5: Local Source Sync

### Goal

Connect Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot parsers/imports to local aggregate storage.

### Scope

- Add source setup and detection for Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot.
- Add manual refresh.
- Ingest aggregate usage events from local source files or supported exports.
- Store aggregate buckets only.
- Record sync runs and source health.
- Back Daily and Weekly views with local source data.
- Support manual/derived allowance windows per source.

### Verification

- Missing source directories show guided setup states.
- Permission-denied source paths show recoverable errors.
- Sync stores aggregate usage without prompts or full transcripts.
- Daily and Weekly views show tool-level splits.
- Cursor behavior is clearly labeled if only partial/manual data is available.
- Gemini CLI behavior is clearly labeled if local telemetry is not configured.
- GitHub Copilot behavior is clearly labeled if only manual or org/admin report data is available.

### Non-Goals

- No WebView account login.
- No internal endpoint scraping.
- No background sync until manual sync is stable.
- No Monthly view.

## PR 6: OpenAI API Cost Source

### Goal

Connect the real OpenAI Admin Usage API and secondary cost paths to local aggregate storage.

### Scope

- Add secure storage for the OpenAI Admin API key.
- Add key validation for usage and costs access.
- Add manual sync.
- Ingest usage buckets.
- Ingest cost buckets when available.
- Record sync runs.
- Surface source health in the Sources view.
- Back Daily and Weekly views with synced local data.

### Verification

- Invalid key shows a recoverable invalid-key state.
- Non-admin or insufficient-permission key shows a permission state.
- Empty usage shows a no-usage state.
- Partial costs show usage normally and mark cost as partial or unavailable.
- Missing allowance data shows consumed usage normally and marks remaining usage as unavailable, manual, or derived.
- Manual sync updates last successful sync and sync-run history.

### Non-Goals

- No automatic background sync unless manual sync is stable.
- No team account management.
- No usage mutation or billing actions.
- No Monthly view.

### Risks To Resolve

- Secure storage behavior across Windows, macOS, and Linux.
- Rate-limit behavior and retry policy.
- How to present API key IDs if names are unavailable.

## PR 7: Trust, Export, And Packaging Check

### Goal

Make the app trustworthy enough for regular local use.

### Scope

- Add CSV or JSON export for aggregate data.
- Add stale-data indicators.
- Add partial-cost indicators near totals.
- Add remaining-usage and refresh/reset indicators.
- Add manual or derived allowance indicators.
- Add clear local cache action.
- Add timezone setting.
- Add data retention setting.
- Run a basic packaging check on Windows.

### Verification

- Exported data contains aggregates only.
- Clearing cache removes local aggregate rows.
- Timezone setting changes Daily/Weekly bucket presentation.
- Partial-cost state is visible in both Daily and Weekly views.
- Missing or manual allowance state is visible in both Daily and Weekly views.
- Windows packaging check completes or documents blocker.

### Non-Goals

- No auto-update system.
- No signed installers.
- No Monthly view unless Daily and Weekly are already stable.

## Post-V1 Candidates

These should not block V1:

- Calendar-week mode.
- Monthly reporting.
- API key aliases.
- Background sync.
- Menu bar or tray glance.
- Budget alerts.
- Allowance alerts.
- Multi-provider usage.
- Additional coding agents beyond Gemini CLI and GitHub Copilot.

## Cross-PR Guardrails

- Keep PRs small and easy to review.
- Do not store prompt, response, request body, or raw transcript data.
- Do not silently show zero cost when costs are unavailable.
- Do not imply exact remaining usage when allowance data is manual, derived, or unavailable.
- Do not introduce Monthly as a first-class route before Daily and Weekly are stable.
- Prefer fixtures and deterministic tests before live API assumptions.
- Any live API behavior discovered in PR 1 should update the PRD before implementation relies on it.
