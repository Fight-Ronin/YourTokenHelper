# Desktop App

Tauri v2 + React + TypeScript desktop shell for YourTokenHelper.

Current desktop scope:

- render Daily and rolling 7-day Weekly from saved or refreshed local aggregate data;
- expose Sources, API Costs, and Settings routes;
- keep API cost secondary;
- start from an empty local aggregate until saved storage or a manual refresh is available.

The header `Refresh` button is a shortcut for the same gated manual refresh
path used by the Sources view. It stays disabled until at least one source root
is present, saved, and the refresh command is not already running; it
does not infer local paths or use a separate sync path.
The Sources view shows explicit-root setup rows for Codex, Claude Code, and
Gemini CLI. The visible `displayValue` is a safe label such
as `Selected, path hidden` or `No root selected`; neither state displays a real
root path.
Those setup rows live in the typed `explicitRootMockRows` fixture. Rows display
typed `pathPolicyLabels`, including `Path hidden` for local/import roots.
Rows also include typed `nextStep` hints: Codex and Claude Code point to
explicit-root setup, and Gemini CLI points to telemetry/export import
without storing local paths in UI payloads.
The fixture also exposes `getManualRefreshReadiness`; it treats the empty-root
default as blocked and any selected explicit import root plus Tauri wiring as
ready. This models the disabled-to-enabled transition without requiring every
source to be configured.
The pure `buildExplicitRootSetupRows` helper can take transient root selections
for any primary local source and return path-free setup rows. It can mark roots
as selected for readiness checks without serializing or displaying supplied
root values.
`applyExplicitRootSetupAction` is the pure picker/manual-entry boundary for
those hidden roots: select actions trim and store only the hidden command draft
value, clear actions remove it, and setup rows still render path-free labels.
`buildManualRefreshDraftFromHiddenRoots` composes those path-free rows with the
manual refresh readiness check. It exposes a trimmed command draft only when at
least one explicit root and bridge wiring are ready; otherwise the draft stays
`null`.
The Sources view consumes that hidden-root boundary with empty roots today, so
it renders path-free setup rows and missing-root readiness while keeping the
refresh action disabled.
The explicit-root rows now use masked manual inputs for the supported local sources
instead of an OS picker. Typed values update only the hidden command draft; the
visible setup rows continue to show path-free labels.
This keeps browser autocomplete and spellcheck disabled.
The Sources view also exposes explicit `Save roots` and `Forget` controls.
Saving writes hidden source roots to a Tauri app-data config file only after
user action; the same config can hold Codex, Claude Code, and Gemini CLI
import roots. The UI continues to show path-free labels and
command responses still do not echo root values. `Forget` clears that local
config. Auto refresh stays disabled until at least one root is ready and saved, then
uses the saved roots while the app is open at a fixed 15-minute interval.
The Sources view imports the production command client behind that gate. It
names `refresh_sources_manual`, tracks running/success/failure states, and keeps
the action disabled in the empty-root default state.
The Sources view also exposes a manual allowance form for primary usage
sources. It accepts only source, unit, numeric allowance fields, and reset time;
successful saves call `save_manual_allowance_window` and promote the returned
storage summary into Daily and Weekly without displaying paths or raw source
ids.
The header `Refresh` shortcut reuses the same command draft and running state,
but requires saved roots so it cannot run from transient unsaved input.
That panel is driven by a typed `manualRefreshMockState` with `canRun: false`,
so the default mock readiness remains centralized while live wiring is present.
It displays the hidden-root boundary's tested path-free needs label, dynamic
root readiness, and tested bridge state, but the empty-root default still does
not invoke refresh or read local source paths.

The UI starts from an empty local aggregate and then promotes saved storage,
manual refresh, manual allowance, or API billing sync results into Daily and
Weekly. The mock fixture remains only as a contract fixture for tests.

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
rendering, marks API cost providers as secondary and unavailable in PR5, and
avoids reusing the mock dollar estimate after live local refresh.
The Source Usage panels then filter that completed map through a tested display
helper: sources with tokens are shown, saved Codex/Claude roots stay visible,
and unconfigured zero-token sources do not take bar space.
The API Costs route is still secondary, but it now reads stored local
`cost_summary` aggregates when OpenAI Admin cost records exist. Missing cost
records render as explicit no-data states. OpenAI live Admin usage/cost sync is
available through the explicit `Sync billing` action after an OpenAI API cost
credential is saved; personal or non-admin keys are expected to return explicit
permission/invalid states instead of fake zero-cost rows.
The provider rows use the shared API cost provider status contract:
OpenAI is `not_configured` until an explicit import or credential path exists,
while Claude, Gemini, and DeepSeek stay `needs_verified_adapter` until official
billing adapters have deterministic fixture coverage.
The API Costs route also exposes provider credential controls backed by Tauri
commands `load_api_provider_credentials`, `save_api_provider_credential`, and
`remove_api_provider_credential`. Credentials are written to the app-data
`api-provider-credentials.json` file only as Windows DPAPI-protected blobs;
returned UI payloads contain provider ids, status, adapter verification, and
credential presence only. They do not return plaintext keys, local paths, raw
provider responses, or plaintext billing payloads. The separate
`sync_api_provider_billing` command accepts only provider id and date on the UI
boundary, injects the decrypted OpenAI key into the backend process environment,
promotes the returned aggregate `storage_summary` into the dashboard, and shows
redacted Usage API / Costs API diagnostics as status labels only.
Claude, Gemini, and DeepSeek remain visible but disabled as
`needs_verified_adapter` until official billing/export adapters are verified.
The Sources page also keeps the returned `refresh_results` in memory for the
current session and renders a `Last Refresh` table with only aggregate sync
metadata: source, status, confidence, event count, and sync-run id. Event count
and sync-run id render as metadata integers, not token totals.
On app startup, `src/commands/loadStorageSummaryClient.ts` calls only the
read-only `load_storage_summary` command and promotes an existing persisted
aggregate into the Daily and Weekly dashboard state. The pure
`src/commands/loadStorageSummaryStartup.ts` helper keeps missing storage,
browser mode, or other invoke failures as unavailable states. Those paths leave
the empty local aggregate visible without creating an empty database, running
refresh, or reflecting local paths.
The Sources view renders the same startup readback state in a `Saved Aggregate`
panel. It labels readback as checking, loaded, or unavailable; the dashboard
row shows saved aggregate, no local aggregate, or mock fallback; and the refresh
row stays manual-or-auto.

It also exposes `buildRefreshSourcesManualArgs`, a pure helper that converts
camelCase UI drafts into the snake_case manual refresh args. Blank optional root
fields are omitted; the helper does not infer, discover, or read local paths.
The runtime Sources action derives `end_day_utc` from the current UTC day with
`manualRefreshEndDayUtc`; the fixed `2026-06-14` date remains only in
deterministic command samples and tests.
The separate gated manual refresh args helper,
`buildGatedRefreshSourcesManualArgs`, requires at least one explicit source root
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
- Gemini CLI root: `experiments/fixtures/local_sources/gemini_cli`

Start the shell with:

```powershell
conda run --no-capture-output -n tokenviz npm run tauri -- dev
```

Automation must request explicit approval before running this GUI smoke. During
manual review, enter any one or all fixture roots in the Sources view masked inputs and
click `Refresh`. Expected result: the Manual Refresh panel reports
`Updated 9,820 aggregate tokens` when all supported fixture roots are supplied, Daily and Weekly switch to
`Live local aggregate`, Last Refresh shows only aggregate sync metadata, and no
fixture root, filename, prompt, response, request body, transcript, tool output,
or code snippet is displayed. Restarting the app should read the saved aggregate
through `load_storage_summary` instead of showing fake zero usage.
To verify saved roots without exposing paths, click `Save roots`, restart, and
confirm the masked inputs are populated, Storage shows `Saved locally`, and the
visible setup rows still do not print the root values. Auto refresh may then be
enabled from the Manual Refresh panel and should reuse the same
`refresh_sources_manual` command at the fixed interval.

`src-tauri/src/lib.rs` exposes a static `source_refresh_summary_sample` command for command-shape checks. It embeds the shared JSON sample at build time; it does not read local files or connect to backend parsers.
The Rust crate also registers the production `refresh_sources_manual` command,
but the command is gated: it requires at least one explicit source root
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
It also registers `load_saved_source_roots`, `save_source_roots`, and
`clear_saved_source_roots` for the explicit-root app-data config. Those commands
trim saved roots, keep auto refresh disabled unless at least one source root is
present, and return fixed redacted errors on config failures.
The desktop TypeScript contract also imports both shared samples, so command
tests do not hand-roll the structured error payload.
