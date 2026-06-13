# PRD: YourTokenHelper V1

Date: 2026-06-13

## Summary

YourTokenHelper V1 is a lightweight desktop app for viewing personal coding-tool usage by day and by week.

The primary user is an individual builder who wants to understand Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, and API-key usage consumption, remaining available usage, and refresh/reset timing without opening a full observability platform.

V1 should be intentionally narrow:

- Daily usage.
- Weekly usage.
- Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot as primary coding-agent sources.
- API-key cost tracking as an additional source when official APIs are available.
- Personal/no-admin mode as the default path with clear manual or derived allowance handling.
- Allowance or quota state as a first-class product concept, whether fetched automatically or entered manually.
- Local aggregate storage.
- Clear sync, permission, and data-quality states.

Monthly reporting is lower priority and should not be a first-class V1 view unless Daily and Weekly are already working well.

## Goals

- Let a user see today's coding-tool usage consumption across Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, and API sources.
- Let a user see rolling 7-day coding-tool usage consumption.
- Let a user see remaining available usage and when the usage window refreshes, when that data is available.
- Break usage down by tool, model, workspace/project, session, and API key when the source provides those fields.
- Show dollar cost as an additional estimate for API-key and token-priced usage, not as the primary product metric.
- Show whether the data is fresh, partial, unavailable, missing allowance data, or missing cost estimates.
- Keep the app local-first after sync: store aggregate buckets, not prompt or response content.

## Non-Goals

- Realtime burn-rate monitoring.
- Prompt-level inspection.
- Full transcript browsing.
- Deep multi-agent workflow analytics.
- Proxy mode or request tracing.
- Team permissions and shared workspaces.
- Full billing reconciliation.
- Exact remaining-usage guarantees when the provider does not expose allowance or refresh data.
- First-class monthly reporting.
- A marketing landing page.

## Target Users

### Individual Coding Tool User

Uses Codex, Claude Code, Cursor, Gemini CLI, or GitHub Copilot across local projects and wants a quick daily/weekly usage view without logging into several dashboards.

### Individual API Builder

Uses API keys directly and wants secondary cost estimates alongside coding-tool subscription usage. May only have a standard personal/project API key.

### Small-Team Operator

Has organization-level Admin API access and wants a quick desktop view of current-week usage, remaining allowance, and refresh timing without building a dashboard.

### Local Codex / Claude Code / Cursor User

Wants the app to read local aggregate usage from coding tools where available, while avoiding prompt or transcript storage.

## Primary Use Cases

### Check Today

As a user, I want to open the app and immediately see today's usage consumption, remaining usage, refresh/reset time, and top drivers.

Acceptance:

- The Daily view loads first after a source is connected.
- Today's total usage, remaining usage, and next refresh/reset time are visible above the fold when available.
- Estimated dollar cost is visible as a secondary metric when cost data is available.
- Top tools, models, workspaces/projects, and API keys are visible without drilling into prompt-level details.

### Check This Week

As a user, I want to understand rolling 7-day usage, remaining account allowance, and whether any day was unusually high.

Acceptance:

- The Weekly view shows rolling 7-day usage consumption.
- The Weekly view shows remaining usage and refresh/reset timing when available.
- A daily trend across the last 7 days is visible.
- Top tools, models, workspaces/projects, and API keys are shown for the week.
- Estimated dollar cost is available as a secondary breakdown.

### Verify Data Trust

As a user, I want to know whether I can trust the numbers shown.

Acceptance:

- Every source shows last successful sync.
- Partial or failed syncs are visible.
- Missing allowance or refresh data is visible near usage status.
- Missing cost estimate data is visible near cost estimates.
- Permission errors are stated plainly.

### Connect Coding Tool Sources

As a user, I want the app to discover Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot usage sources so I can see daily and weekly usage without account scraping.

Acceptance:

- The app can show whether Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot data sources are detected or available.
- The app reads aggregate usage fields only.
- The app does not store prompts, tool output, code snippets, or full transcripts.
- The app can mark a source as ready, missing, unsupported, permission denied, or needs manual setup.

### Connect OpenAI API Cost Source

As a user with Admin API access, I want to connect an OpenAI Admin API key so the app can fetch official account/API organization usage.

Acceptance:

- The app explains that an Admin API key is required for official organization usage sync.
- The app does not imply that every personal account can provide an Admin API key.
- The app can validate whether the key has access to organization usage.
- The app can detect whether costs and allowance/refresh data are available or need fallback handling.
- The key can be replaced or removed.
- The key is stored in OS secure storage, not plaintext SQLite.

## Data Source Requirements

### Account Type Distinction

The product should distinguish two related but different concepts:

- Local coding-tool usage: aggregate token/credit/cost signals from Codex, Claude Code, Cursor, Gemini CLI, and locally observable sources on this machine.
- Official/report usage: aggregate GitHub Copilot usage where official metrics/report access is available.
- API organization usage: usage and cost data associated with OpenAI API activity.
- Account allowance: remaining available usage and refresh/reset timing for the user's account or plan.

V1 should lead with local personal usage. If official API organization usage is available but account allowance is not, the UI should say so clearly instead of treating API cost data as remaining account usage.

### Local Coding Tool Sources

V1 should support Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot as primary source types.

The local source spike should verify:

- Platform-specific data directories on Windows, macOS, and Linux.
- Whether each source exposes timestamp, model, token counts, session/workspace IDs, and cost/credit hints.
- Whether the source can be parsed without retaining prompts or full transcripts.
- Whether source data covers only this machine or can include cloud/web usage.
- Whether reset/remaining usage appears locally or must be manual/derived.

### OpenAI Admin Usage API

V1 should use the OpenAI Administration Usage API for official API-key usage/cost data when available. This is an additional source, not the main personal coding-tool path.

The PR 1 API spike should verify:

- Endpoint path and parameters for completions usage.
- Supported bucket widths.
- Pagination behavior.
- Supported grouping by `api_key_id`, `model`, `project_id`, and `user_id`.
- Whether `reasoning_output_tokens` is always returned for relevant models or only sometimes.
- Whether API key names can be fetched separately or only key IDs are available in usage results.

### Account Allowance And Refresh State

V1 should treat account allowance as a first-class concept:

- Usage consumed.
- Remaining available usage.
- Usage window start.
- Usage window end or refresh/reset time.
- Confidence/source of allowance data.

The PR 1 API spike should verify whether OpenAI exposes allowance, remaining usage, and refresh/reset timing through an official API for the target account type.

If no official API is available, V1 should support a fallback design:

- User-entered allowance limit.
- User-entered refresh/reset time.
- Derived remaining usage from synced usage buckets.
- A clear label such as "manual estimate" or "derived estimate".

### OpenAI Costs API

V1 should use the OpenAI Costs API for secondary API-key dollar estimates when available.

The PR 1 API spike should verify:

- Endpoint path and parameters for costs.
- Whether cost buckets can be grouped by `api_key_id`, `project_id`, and line item.
- Whether model-level cost attribution is available directly or must be inferred.
- How costs align with usage buckets across timezone and bucket boundaries.

### Admin API Key Constraint

The app must explain that official organization usage requires an OpenAI Admin API key. Admin API keys are for administration endpoints and should not be used as normal inference API keys.

Personal accounts or standard project API keys may not be able to access organization usage/cost endpoints. V1 should treat this as a normal setup state and offer personal/no-admin mode instead of blocking the whole app.

The app must also explain that remaining available usage and refresh/reset timing may require separate support from the provider. If that data is not available through an API, the app should label remaining usage as manual or derived.

## Information Architecture

### Daily

Default connected-state screen.

Top metrics:

- Usage consumed today.
- Remaining available usage.
- Next refresh/reset time.
- Cost estimate today.
- Requests today.
- Cached input share.

Breakdowns:

- By API key.
- By model.
- By project.

Status:

- Last synced at.
- Source health.
- Allowance data status.
- Cost estimate coverage.

### Weekly

Rolling 7-day view.

Top metrics:

- Rolling 7-day usage consumed.
- Remaining available usage.
- Next refresh/reset time.
- Rolling 7-day cost estimate.
- Rolling 7-day requests.
- Average daily tokens.

Visual:

- Daily trend for the last 7 days.

Breakdowns:

- Top tools/sources.
- Top models.
- Top workspaces/projects/API keys.

### API Costs

Secondary page for official API-key usage and dollar costs when Admin API access is available.

Top metrics:

- Rolling 7-day API cost.
- Today's API cost.
- API usage tokens.
- Source permission status.

Breakdowns:

- By API key when available.
- By project when available.
- By model when available or inferable.

This page should not block Codex, Claude Code, or Cursor local usage.

### Sources

Source setup and health.

Sections:

- Codex local source.
- Claude Code local source.
- Cursor local source.
- Gemini CLI source.
- GitHub Copilot source.
- OpenAI API cost source.

Source states:

- Not connected.
- Connected.
- Syncing.
- Last sync failed.
- Permission denied.
- Usage available but costs unavailable.
- Usage available but allowance unavailable.
- Allowance configured manually.
- No usage found.

### Settings

Configuration and local data controls.

Controls:

- Enable, disable, or rescan Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot sources.
- Replace OpenAI Admin API key for optional API cost sync.
- Remove OpenAI Admin API key.
- Configure manual allowance or refresh/reset time.
- Manual sync.
- Timezone.
- Data retention period.
- Clear local aggregate cache.
- Export aggregate data.

## Data Fields

### Usage Bucket

Required fields:

- Source ID.
- Bucket start.
- Bucket end.
- Granularity.
- Input tokens.
- Output tokens.
- Cached input tokens.
- Request count.

Optional fields:

- API key ID.
- API key alias.
- Source kind.
- Model.
- Workspace ID.
- Session ID.
- Project ID.
- User ID.
- Reasoning output tokens.

### Cost Bucket

Required fields:

- Source ID.
- Bucket start.
- Bucket end.
- Granularity.
- Amount.
- Currency.

Optional fields:

- API key ID.
- Model.
- Project ID.
- Line item.

### Allowance Window

Required fields:

- Source ID.
- Window start.
- Window end or reset time.
- Usage limit.
- Usage consumed.
- Remaining usage.
- Unit.
- Confidence.
- Data source.

Optional fields:

- Account ID.
- Project ID.
- Notes.

### Sync Run

Required fields:

- Source ID.
- Started at.
- Finished at.
- Status.
- Error code.
- Error message.
- Rows fetched.

## UX States

### First Launch

Show a setup view with one primary action:

- Detect local coding tool sources.

Secondary action:

- Explore with sample data.
- Connect optional API cost source.

The first launch view should not look like a marketing page.

### No Usage Found

Explain that the source is valid but no usage was returned for the selected time range.

Offer:

- Change date range.
- Retry sync.
- Check that the selected local tool or API organization is correct.

### Permission Error

Explain that the source cannot be read or the key cannot access the required endpoint.

Offer:

- Rescan local source.
- Replace key for API cost source.
- Link to official Admin API key setup when relevant.

### Partial Cost Data

Show usage totals normally, but mark cost estimates as partial or unavailable.

Do not silently show zero cost when costs are missing.

### Missing Allowance Data

Show consumed usage normally, but mark remaining usage and refresh/reset timing as unavailable or manual.

Do not imply exact remaining usage if it is derived from a user-entered limit.

### Stale Data

Show the last successful sync timestamp and a manual sync action.

## Privacy And Security

- Store API keys in OS secure storage.
- Store only aggregate usage and cost buckets locally.
- Store allowance settings and derived allowance windows locally.
- Do not store prompts, responses, tool output, code snippets, request payloads, raw local transcripts, or raw API logs.
- Do not send usage data to any third-party service.
- Allow users to clear local aggregate data.
- Local source access should be opt-in and clearly labeled by source.

## V1 Success Metrics

Qualitative:

- A user can connect a source and understand today's coding-tool usage without reading docs.
- A user can see remaining available usage and refresh/reset timing when available or configured.
- A user can identify the top tool, model, workspace/project, or API key for the current week.
- A user can tell whether allowance and cost data are complete, manual, derived, or unavailable.

Functional:

- Discovers Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot source capability.
- Fetches or parses daily usage buckets.
- Fetches, parses, or estimates daily cost buckets that can be aggregated into weekly summaries.
- Persists allowance windows or manual allowance settings.
- Displays daily and weekly summaries from local storage.
- Handles not-found source, unsupported source, invalid key, permission denied, rate limit, empty usage, missing allowance data, and partial costs.

## Proposed Build Sequence

### PR 1: OpenAI API Cost Spike

Validate the OpenAI Usage, Costs, and allowance/refresh availability for the optional API-key cost source.

Output:

- Sanitized fixture examples.
- Notes on grouping, pagination, bucket boundaries, and error states.
- Notes on whether remaining usage and refresh/reset timing can be fetched automatically.
- Recommendation for local schema adjustments.

### PR 1b: Local Source Discovery Spike

Validate Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot usage sources.

Output:

- Redacted capability report for the coding-agent sources.
- Notes on local paths, available fields, and privacy risks.
- Recommendation for which source parser to implement first.

### PR 2: Parser Contract And Fixtures

Define the normalized usage event contract and deterministic parser fixtures.

Output:

- Unified usage event shape.
- Fixture-driven parser tests for ready local sources.
- API cost fixture coverage.

### PR 3: Desktop Shell With Mock Data

Create the Tauri + React desktop app skeleton with static mock data.

Output:

- Daily, Weekly, Sources, and Settings navigation.
- Mock Daily and Weekly views with Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, API usage consumed, remaining usage, refresh/reset time, and secondary cost estimate.
- First-pass layout and empty states.

### PR 4: Local Storage

Add SQLite aggregate storage.

Output:

- Tables for sources, usage buckets, cost buckets, allowance windows, and sync runs.
- Query layer for Daily and Weekly summaries.

### PR 5: Local Source Sync

Connect Codex, Claude Code, Cursor, Gemini CLI, and GitHub Copilot sources to local aggregate storage or supported official/report import.

Output:

- Manual local sync.
- Aggregate usage ingestion.
- Tool/source health states.
- Manual or derived allowance fallback.

### PR 6: OpenAI API Cost Source

Connect the real OpenAI API cost source.

Output:

- Secure key storage.
- Manual sync.
- Usage ingestion.
- Cost estimate ingestion when available.
- Allowance ingestion or manual allowance fallback.
- Source health states.

### PR 7: Trust And Polish

Make the app reliable enough to use daily.

Output:

- Export aggregate data.
- Partial-cost indicators.
- Missing-allowance or manual-estimate indicators.
- Stale-data indicators.
- Clear local cache.
- Basic packaging check.

## Open Questions

- Should Weekly mean rolling last 7 days, calendar week, or both?
- Should V1 fetch 14 days, 30 days, or 90 days on first sync?
- Should API key aliases be user-defined in V1 if official names are not available in usage buckets?
- Can remaining available usage and refresh/reset timing be observed locally for Codex, Claude Code, or Cursor?
- If allowance data is not available locally or through API, should V1 require manual allowance setup or still ship with consumed-usage-only mode?
- What unit should allowance use in the UI: tokens, credits, dollars, requests, or provider-specific usage units?
- Should sample data mode ship in V1, or only be used during development?
- Is Cursor parser-ready, or should it start as manual/export-only?
- When should Monthly be promoted from lower-priority follow-up to a first-class view?

## References

- Research: `docs/token-usage-viewer-research.md`
- PR 0 plan: `docs/pr-0-plan.md`
- Source strategy: `docs/source-strategy-v1.md`
- OpenAI Usage API: https://platform.openai.com/docs/api-reference/usage
- OpenAI Administration overview: https://developers.openai.com/api/reference/administration/overview
### Gemini CLI Telemetry

V1 should support Gemini CLI through explicit local telemetry/export data.

The parser must whitelist token/model/time fields and must not persist telemetry prompt or response text.

### GitHub Copilot Usage Metrics

V1 should support GitHub Copilot through official usage metrics/report data when available.

Personal local token usage is not assumed. If only local app state is detected without token fields, V1 should show a setup/manual state instead of implying parser readiness.
