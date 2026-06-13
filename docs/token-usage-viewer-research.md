# Token Usage Viewer Research

Date: 2026-06-13

## Scope

We are not building a "25 agents" aggregator for v1. The target is a lightweight desktop viewer that helps a specific user understand daily and weekly personal coding-tool usage, remaining available usage, and refresh/reset timing. Monthly reporting is lower priority.

Four usage sources are relevant:

- Codex local usage: primary v1 source.
- Claude Code local usage: primary v1 source.
- Cursor local usage or supported exports: primary v1 source, but needs source-shape validation.
- Gemini CLI telemetry/export usage: primary v1 source, but should require whitelist parsing because telemetry can include prompt/response text.
- GitHub Copilot official usage metrics/report usage: primary v1 source, but personal local token access is not assumed.
- Official API usage/cost: useful for API-key level OpenAI cost because the Administration Usage API can group usage by API key, model, project, and user when Admin API access is available.
- Account allowance data: needed for remaining available usage and refresh/reset timing. PR 1 must verify whether this can be fetched automatically; otherwise the app should support manual or derived estimates.

## Competitor Findings

### ccusage

Repo: https://github.com/ccusage/ccusage

What worked:

- Ran successfully on Windows using the native npm package `@ccusage/ccusage-win32-x64` without installing npm.
- Commands tested:
  - `ccusage.exe --help`
  - `ccusage.exe codex daily --offline`
  - `ccusage.exe codex monthly --offline`
  - `ccusage.exe codex daily --json --since 2026-06-13 --offline`
  - `ccusage.exe codex monthly --json --offline`

Design takeaways:

- Daily and monthly are first-class commands; weekly summaries can be derived from daily buckets for our v1.
- JSON output is clean enough to treat as a reference schema: date/month, input, output, reasoning output, cache read/create, total, cost, models.
- Missing pricing is handled visibly with a warning. This is better than silently treating missing models as zero-cost.
- Native binary distribution is attractive for a lightweight desktop app because a small scanner binary can run without Node/npm.

Gaps:

- Terminal-first UX.
- No account/API-key OAuth/Admin API flow.
- Local-log focused, not a simple "my OpenAI account/API key daily/weekly usage" product.

### Claude Code Usage Monitor

Repo: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor

What worked:

- Installed in a temporary Python venv from PyPI as `claude-monitor==3.1.0`.
- `claude-monitor --help` worked.
- With a workspace-local temporary home, `claude-monitor --view daily` and `--view monthly` ran and reported no Claude data directory.

Observed friction:

- With the real home path inside the sandbox, it tried to write `~/.claude-monitor` and failed with a permission error.
- It searches `~/.claude/projects` and `~/.config/claude/projects`.

Design takeaways:

- Realtime burn-rate/session-window monitoring is powerful, but too much for our v1 if daily/weekly is the goal.
- A desktop app should use platform app-data directories and show a recoverable "storage permission" state.
- Empty state matters: "No data directory found" should become a guided source setup card.

Gaps:

- Terminal-first.
- Claude-specific.
- More complex than daily/weekly usage monitoring.

### Codex Usage Desktop

Repo: https://github.com/itvincent-git/codex-usage-desktop

What was verified:

- Latest release checked via GitHub Releases API: `app-v1.8.1`, published 2026-06-12.
- Release assets are macOS only: DMG and macOS app archives.
- Source stack: React, Vite, Tauri v2, Rust usage pipeline.

Design takeaways:

- This is the closest product analogue for an aggregate desktop usage dashboard, though it emphasizes daily/monthly rather than daily/weekly.
- Strong positioning: local-first, no API key, no upload, SQLite cache.
- It validates that aggregate usage can be enough for a useful app.

Gaps:

- macOS-only release today.
- Codex-only.
- README says unknown models default to zero cost.
- No account/API-key view.

### TokenBar

Repo: https://github.com/Nanako0129/TokenBar

What was verified:

- Latest release checked via GitHub Releases API: `v1.0.2`, published 2026-06-12.
- Release asset is `TokenBar.app.tar.gz`; macOS-only.
- Tech stack: Swift menu bar shell plus Rust parsing/pricing core.

Design takeaways:

- Menu bar/tray glance is valuable: today tokens, cost, live rate, quota remaining.
- It shows users like passive monitoring, not only opening a dashboard.

Gaps:

- macOS 14+ and Apple Silicon focused.
- Too broad for our v1.
- More playful/visual than the calm utility we likely want.

### Codex Usage Tracker

Repo: https://github.com/douglasmonsky/codex-usage-tracker

What worked:

- Installed in the same temporary Python venv from PyPI as `codex-usage-tracking==0.5.0`.
- `codex-usage-tracker doctor` worked and found local Codex sessions.
- `refresh --json` worked with a workspace-local SQLite DB.
- `summary`, `query`, and static `dashboard` generation worked.

Design takeaways:

- Strong local-first data model: aggregate metrics in SQLite, no prompts/tool output stored.
- Useful insight concepts: pricing gaps, large cumulative thread, context bloat, cache ratio.
- Excellent diagnostic/doctor approach for power users.

Gaps:

- Power-user CLI/dashboard, not a small desktop viewer.
- Natural monthly UX is not prominent; the CLI has `today` and `last-7-days`, but not a simple `this-month` preset.
- Setup concepts like refresh/index/db/dashboard should be hidden behind desktop onboarding.

## OpenAI Official API Notes

Official docs:

- Usage API: https://platform.openai.com/docs/api-reference/usage
- Administration API overview: https://developers.openai.com/api/reference/administration/overview

Relevant facts:

- Usage endpoints live under Administration / Organization usage, for example `GET /organization/usage/completions`.
- The completions usage result includes input tokens, output tokens, cached input tokens, request count, model, project ID, user ID, and API key ID when grouped by those dimensions.
- Costs are available at `GET /organization/costs`.
- Administration APIs require an Admin API key. Admin API keys are for administration endpoints, not normal inference calls.

Product implication:

- For personal coding-tool monitoring, local source parsing is the most valuable default path. We should support an optional OpenAI Admin API connector for true account/API-key daily/weekly usage and cost when available.
- Remaining available usage and refresh/reset timing are product-critical but not yet proven to be API-accessible. The product should label allowance data as API-backed, manual, derived, or unavailable.
- This should be opt-in, securely stored, and clearly labeled as "OpenAI organization usage" rather than "local app usage".

## Recommended MVP

V1 should be a two-tab desktop utility:

1. Daily
   - Today usage consumed across Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, and API sources
   - Remaining available usage
   - Next refresh/reset time
   - Today estimated dollar cost as a secondary metric
   - Token split: input, output, cached input, reasoning output where available
   - Breakdown by tool/source/model/workspace/API key
   - Last refreshed time and data source health

2. Weekly
   - Rolling 7-day usage consumed across Codex, Claude Code, Cursor, Gemini CLI, GitHub Copilot, and API sources
   - Remaining available usage
   - Next refresh/reset time
   - Rolling 7-day estimated dollar cost as a secondary metric
   - Daily trend across the last 7 days
   - Breakdown by tool/source/model/workspace/API key
   - Allowance and cost estimate coverage warnings

Monthly reporting should stay lower priority until Daily and Weekly are useful.

## Source Strategy

Start with four source types:

- Codex local source: primary path if local usage-bearing data is available.
- Claude Code local source: primary path if local usage-bearing data is available.
- Cursor local source or export: primary path if local usage-bearing data is available; otherwise manual/partial source.
- Gemini CLI telemetry/export source: primary path if local telemetry is explicitly configured.
- GitHub Copilot usage metrics/report source: primary path when official access is available; otherwise manual/partial source.
- API-key cost source: optional OpenAI Admin Usage/Costs API when `api.usage.read` access is available.
- Account allowance source: API-backed if available, otherwise manual or derived estimate per source.

Defer:

- Realtime burn rate.
- Session/thread drilldowns.
- Multi-agent integrations.
- Team dashboards.
- LLMOps tracing/proxy mode.
- WebView login or internal endpoint scraping for personal accounts.

## Product Principles

- Daily/weekly first. Avoid session-level detail unless a user drills down.
- Never silently price unknown models as zero.
- Never imply exact remaining usage when allowance data is manual, derived, or unavailable.
- Make source health visible but quiet.
- Store only aggregates by default.
- Keep API key setup explicit and reversible.
- Prefer local personal sources over account scraping.
- Support Windows/macOS/Linux from the first packaged release.
