# Desktop App

Tauri v2 + React + TypeScript desktop shell for YourTokenHelper.

PR3 scope:

- render Daily and rolling 7-day Weekly from static mock aggregate data;
- expose Sources, API Costs, and Settings routes;
- keep API cost secondary;
- do not connect to real local parsers, SQLite, or live APIs.

Header sync and setup affordances are disabled in the mock shell. They preserve
the future layout contract without implying that local source sync is wired.
The Sources view also shows disabled explicit-root setup rows for Codex and
Claude Code; these rows do not open a picker, call Tauri, or read local paths.
Codex is tracked as `Selected (mock)` while Claude Code remains `Not selected`,
but the visible `displayValue` is a safe label such as
`Selected, path hidden` or `No root selected`; neither state stores or displays
a real root path.
Those setup rows live in the typed `explicitRootMockRows` fixture, which keeps
Cursor, Gemini CLI, and GitHub Copilot as status-only/report-only paths.
Rows also display typed `pathPolicyLabels` so status-only sources are labeled as
`No local parser` and report-only sources stay labeled as `Official report`.
Rows also include typed `nextStep` hints so Codex and Claude Code point to
explicit-root setup, Cursor stays manual/status-only, Gemini CLI points to
telemetry/export setup, and GitHub Copilot points to official reports without
storing local paths.
The fixture also exposes `getManualRefreshReadiness`; it treats Codex's
`Selected (mock)` label as still missing an explicit root, so mock mode cannot
accidentally enable refresh from label-only state.
The readiness helper also models the future disabled-to-enabled transition:
only selected Codex and Claude Code roots plus explicit Tauri wiring can produce
`canRun: true`. The mock UI still passes the default unwired state.
The pure `buildExplicitRootSetupRows` helper can take transient Codex and
Claude Code root selections and return path-free setup rows. It can mark roots
as selected for readiness checks without serializing or displaying the supplied
root values.
`applyExplicitRootSetupAction` is the pure future picker boundary for those
hidden roots: select actions trim and store only the hidden command draft value,
clear actions remove it, and setup rows still render path-free labels.
`buildManualRefreshDraftFromHiddenRoots` composes those path-free rows with the
manual refresh readiness check. It exposes a trimmed command draft only when
both explicit roots and bridge wiring are ready; otherwise the draft stays
`null`.
The Sources view consumes that hidden-root boundary with empty roots today, so
it renders path-free setup rows and missing-root readiness while keeping the
refresh action disabled.
The explicit-root rows now use masked manual inputs for Codex and Claude Code
instead of an OS picker. Typed values update only the hidden command draft; the
visible setup rows continue to show path-free labels.
This keeps browser autocomplete and spellcheck disabled.
The Sources view imports the production command client behind that gate. It
names `refresh_sources_manual`, tracks running/success/failure states, and keeps
the action disabled in the empty-root default state.
That panel is driven by a typed `manualRefreshMockState` with `canRun: false`,
so the default mock readiness remains centralized while live wiring is present.
It displays the hidden-root boundary's tested path-free needs label, dynamic
root readiness, and tested bridge state, but the empty-root default still does
not invoke refresh or read local source paths.

The mock UI reads `src/data/mock-v1-summary.json`, copied from the backend-owned contract fixture at `../../backend/fixtures/mock_v1_summary.json`.

`src/types.ts` also mirrors the PR5 refresh-summary command payload for Tauri wiring. The current desktop shell keeps that command behind explicit-root readiness and does not read real source data by default.

The backend Codex and Claude Code JSONL adapters now support the repository
aggregate `usage` fixture shape plus the observed local token fields:
`payload.info.last_token_usage` for Codex and `message.usage` for Claude Code.
They build aggregate `UsageEvent` rows without storing prompt text, response
text, message content, tool output, code snippets, filenames, or local paths.

`src-tauri/source-refresh-summary.sample.json` is the shared static sample for that PR5 payload. `src/data/source-refresh-summary.sample.ts` exposes a typed import, and backend tests verify the JSON matches the generated fixture. Neither file is imported by the UI.

`src/commands/sourceRefreshSummary.ts` defines typed command names and contracts for future Tauri wiring, including the static sample command and the production manual refresh command. It does not import Tauri or invoke either command.
`src/commands/refreshSourcesManualInvoker.ts` adds the dependency-injected
frontend invocation boundary for that production command. It requires gated
manual refresh args before calling Tauri, calls only `refresh_sources_manual`,
never falls back to `source_refresh_summary_sample`, and converts thrown
browser/Tauri failures into `Manual refresh unavailable` without reflecting
exception text or local paths.
`src/commands/refreshSourcesManualClient.ts` is the thin runtime wrapper that
passes Tauri's `invoke` into that boundary. The Sources view imports this
wrapper only behind the hidden-root readiness gate, and the empty-root default
state keeps the action disabled.
When a gated manual refresh succeeds, the React shell promotes the returned
`storage_summary` into the Daily and Weekly dashboard state through
`src/data/dashboard-summary.ts`. That normalizer completes the source map for UI
rendering, marks OpenAI API Cost as secondary and unavailable in PR5, and avoids
reusing the mock dollar estimate after live local refresh.
The Sources page also keeps the returned `refresh_results` in memory for the
current session and renders a `Last Refresh` table with only aggregate sync
metadata: source, status, confidence, event count, and sync-run id. Event count
and sync-run id render as metadata integers, not token totals.
On app startup, `src/commands/loadStorageSummaryClient.ts` calls only the
read-only `load_storage_summary` command and promotes an existing persisted
aggregate into the Daily and Weekly dashboard state. The pure
`src/commands/loadStorageSummaryStartup.ts` helper keeps missing storage,
browser mode, or other invoke failures as unavailable states. Those paths leave
the mock summary visible without creating an empty database, running refresh,
showing zero usage, or reflecting local paths.
The Sources view renders the same startup readback state in a `Saved Aggregate`
panel. It labels readback as checking, loaded, or unavailable; the dashboard
row shows either saved aggregate or mock fallback; and the refresh row stays
manual-only.

It also exposes `buildRefreshSourcesManualArgs`, a pure helper that converts
camelCase UI drafts into the snake_case manual refresh args. Blank optional root
fields are omitted; the helper does not infer, discover, or read local paths.
The runtime Sources action derives `end_day_utc` from the current UTC day with
`manualRefreshEndDayUtc`; the fixed `2026-06-14` date remains only in
deterministic command samples and tests.
The separate gated manual refresh args helper,
`buildGatedRefreshSourcesManualArgs`, requires both Codex and Claude Code roots
before producing args for future live refresh wiring. It reuses the same
structured `invalid_refresh_request` payload and still does not infer,
discover, or read local paths.
Run `npm run test:commands` to compile and execute the helper's dependency-free
runtime contract checks.
Those checks cover the manual refresh args builder, command-name separation, the
success/error result type guards, shared success/error samples, the static
aggregate sample totals, the production command invoker boundary, and the mock
source setup state. They also cover refresh-to-dashboard normalization so
partial local-source summaries do not silently become API cost data.

Run `npm run typecheck` to verify the desktop types and contract samples without building the Vite bundle.

## Synthetic PR5 desktop smoke

The review-only desktop smoke uses repository synthetic fixtures, not real local
user directories:

- Codex root: `experiments/fixtures/local_sources/codex`
- Claude Code root: `experiments/fixtures/local_sources/claude_code`

Start the shell with:

```powershell
conda run -n tokenviz npm run tauri -- dev
```

Automation must request explicit approval before running this GUI smoke. During
manual review, enter the two fixture roots in the Sources view masked inputs and
click `Refresh`. Expected result: the Manual Refresh panel reports
`Updated 7,570 aggregate tokens`, Daily and Weekly switch to
`Live local aggregate`, Last Refresh shows only aggregate sync metadata, and no
fixture root, filename, prompt, response, request body, transcript, tool output,
or code snippet is displayed. Restarting the app should read the saved aggregate
through `load_storage_summary` instead of showing fake zero usage.

`src-tauri/src/lib.rs` exposes a static `source_refresh_summary_sample` command for command-shape checks. It embeds the shared JSON sample at build time; it does not read local files or connect to backend parsers.
The Rust crate also registers the production `refresh_sources_manual` command,
but the command is gated: it requires explicit Codex and Claude Code roots
before spawning the backend process and returns structured
`invalid_refresh_request` errors without echoing supplied root values.
It mirrors the manual refresh args as a snake_case `RefreshSourcesManualArgs`
struct with unknown fields denied.
The same Rust module mirrors the manual refresh result union as
`RefreshSourcesManualResult`, distinguishing aggregate success payloads from
structured `invalid_refresh_request` errors by using the embedded static samples.
It also names the backend process module `backend.sources.refresh_command_cli`
and provides helpers for manual refresh stdin serialization, backend process
invocation, and stdout result parsing. The registered command and process helper
are covered by synthetic fixture tests and do not call the static sample command
as a live fallback. The backend CLI can use an internal
`YTH_REFRESH_DATABASE_PATH` environment variable for file-backed SQLite process
tests, but the React command args do not include a database path and the UI does
not display one. Rust process tests pass that environment variable to the
backend helper and verify that a later process can read the same aggregate
SQLite summary without echoing the database path. For normal Tauri command
execution, Rust resolves the default refresh database path from Tauri's app-data
directory before spawning the backend process; the env var remains an internal
override.
The Rust crate also registers a read-only `load_storage_summary` command that
uses the same internal app-data database path, returns only the aggregate storage
summary shape, and reports unavailable storage with a structured error instead
of creating an empty database or showing fake zero usage.
The desktop TypeScript contract also imports both shared samples, so command
tests do not hand-roll the structured error payload.
