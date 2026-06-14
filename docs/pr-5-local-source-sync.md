# PR 5 Local Source Sync

Date: 2026-06-14

## Goal

Connect the first mature local aggregate sources to SQLite storage behind a manual refresh boundary.

The current PR5 backend path supports:

- Codex from an explicit aggregate JSONL root.
- Claude Code from an explicit aggregate JSONL root.
- Cursor as a manual-only status until a stable aggregate source is verified.
- Gemini CLI as setup-required until explicit telemetry or export setup is available.
- GitHub Copilot as an official-report path; personal local token parsing is not assumed.

## Handoff Payload

The command-shaped backend helper is `build_primary_refresh_command_payload`.
It accepts only explicit Codex and Claude Code JSONL roots; it does not infer
default local paths.

The Codex adapter supports both the synthetic aggregate `usage` fixture shape
and observed local rollout records with token totals under
`payload.info.last_token_usage`; it falls back to
`payload.info.total_token_usage` only when a last-token usage block is absent.
The Claude Code adapter supports both the synthetic aggregate `usage` fixture
shape and observed local records with token totals under `message.usage`.
Both adapters ignore prompt, response, message content, tool output, code
snippets, session filenames, and local paths when building `UsageEvent` rows.

The returned payload has this top-level shape:

```json
{
  "refresh_results": [],
  "storage_summary": {}
}
```

`refresh_results` is ordered by the source registry and contains only sync metadata:

- `source_kind`.
- `source_id`.
- `status`.
- `confidence`.
- `events_seen`.
- `sync_run_id`.
- `message`, when the source has a generic setup or health message.

`storage_summary` reuses the existing Daily and rolling 7-day storage summary shape:

- `schema_version`.
- `generated_from`.
- `privacy`.
- `summary`.
- `allowance_windows`.
- `source_states`.

## Fixture Export

The deterministic fixture exporter is:

```powershell
python -m backend.fixtures.source_refresh_summary --output .probe-output/source-refresh-summary.json
```

It uses only synthetic fixture roots under `experiments/fixtures/local_sources`.

Expected aggregate result for `2026-06-14`:

| Source | Events seen | Total tokens |
| --- | ---: | ---: |
| Codex | 2 | 2540 |
| Claude Code | 2 | 5030 |
| Cursor | 0 | 0 |
| Gemini CLI | 0 | 0 |
| GitHub Copilot | 0 | 0 |
| Total | 4 | 7570 |

## Synthetic Desktop Acceptance Smoke

This is the PR5 manual review checklist for proving the desktop chain without
reading real local user directories. It uses only the repository-owned
synthetic fixture roots under `experiments/fixtures/local_sources`.

Run the desktop shell with Tauri from `apps/desktop`:

```powershell
conda run -n tokenviz npm run tauri -- dev
```

If automation runs this GUI smoke instead of a human reviewer, it must request
explicit approval first. The smoke should not use live API calls, network
access, or default local path discovery.

Use these synthetic roots in the Sources view masked inputs:

| Source | Fixture root |
| --- | --- |
| Codex | `experiments/fixtures/local_sources/codex` |
| Claude Code | `experiments/fixtures/local_sources/claude_code` |

Expected review outcomes:

- The visible setup rows still show path-free labels such as
  `Selected, path hidden`; the typed root values are not echoed elsewhere.
- The Manual Refresh panel changes from blocked to ready once both roots are
  present, then the `Refresh` button invokes only `refresh_sources_manual`.
- The result message is `Updated 7,570 aggregate tokens`.
- Daily and rolling 7-day Weekly switch to `Live local aggregate` and show the
  same 7,570 aggregate-token fixture total.
- The Last Refresh table shows only source, status, confidence, event count,
  and sync-run id metadata; it does not show fixture roots, filenames, prompt
  text, response text, request bodies, raw transcripts, tool output, or code
  snippets.
- Restarting the desktop shell should load the saved aggregate through
  `load_storage_summary` without creating a fake zero-usage summary.
- Cursor remains manual/status-only, Gemini CLI remains setup-required, GitHub
  Copilot remains official-report/manual, and OpenAI API Cost remains a
  secondary unavailable source.

## Privacy Boundary

The handoff payload must not include:

- Prompt text.
- Response text.
- Request bodies.
- Raw transcripts.
- Tool output.
- Code snippets.
- Source roots, paths, filenames, or local user directory names.

Only aggregate usage buckets, source states, and generic sync metadata are exposed.

## Command Boundary

The command boundary currently supports:

- Command name for the future production manual refresh path:
  `refresh_sources_manual`.
- `codex_jsonl_root`, optional explicit path.
- `claude_code_jsonl_root`, optional explicit path.
- `end_day_utc`, required rolling 7-day end date in strict `YYYY-MM-DD` format.
- `started_at`, optional synthetic or caller-provided ISO-8601 refresh timestamp.

The backend request contract is `PrimaryRefreshCommandRequest`, parsed from
command arguments by `primary_refresh_command_request_from_mapping`. Unknown
fields are rejected so the command cannot silently enable default local path
discovery.

The JSON bridge helpers `build_primary_refresh_command_response_from_json` and
`build_primary_refresh_command_response_json` reuse the same mapping boundary
for future desktop bridge work. They parse command args JSON, reject invalid or
non-object JSON with structured `invalid_refresh_request` errors, and do not
echo supplied root values.

Invalid refresh request errors can be converted with
`primary_refresh_command_error_to_payload`. Error payloads use the code
`invalid_refresh_request`, may include a field name, and must not echo supplied
source path values.

The future Tauri command should call
`build_primary_refresh_command_response_from_mapping` or an equivalent boundary
that returns the same success/error union instead of leaking validation
exceptions directly.
For process-style bridge wiring, `backend.sources.refresh_command_cli` exposes
a stdin/stdout wrapper around `build_primary_refresh_command_response_json`.
It accepts the same explicit-root JSON args and writes the same
aggregate-only success/error union without echoing supplied roots.

When no explicit roots are provided, Codex and Claude Code return setup states
and no usage events are stored. Cursor, Gemini CLI, and GitHub Copilot remain
status-only paths until their source maturity changes.

## Desktop Type Mirror

The desktop TypeScript mirror lives in `apps/desktop/src/types.ts` as:

- `RefreshResult`.
- `RefreshStorageSummaryPayload`.
- `SourceRefreshSummaryPayload`.

These types are a contract mirror for the refresh result. The desktop still
reads static mock data by default, while the Sources manual refresh action now
imports the production command client behind the explicit-root readiness gate.

The command-name shim lives in
`apps/desktop/src/commands/sourceRefreshSummary.ts`. It defines the static Tauri
sample command contract and the production manual refresh command contract for
future wiring, including the structured invalid-request error result, but it
does not import Tauri or invoke either command. It also exposes TypeScript type
guards for distinguishing success payloads from structured error payloads.
`apps/desktop/src/commands/refreshSourcesManualInvoker.ts` adds a
dependency-injected frontend invocation boundary for the production command. It
requires gated manual refresh args, invokes only `refresh_sources_manual`, and
never falls back to `source_refresh_summary_sample`. Thrown browser/Tauri
failures become a fixed `Manual refresh unavailable` result so exception text
cannot echo local paths.
`apps/desktop/src/commands/refreshSourcesManualClient.ts` is the thin runtime
wrapper that passes Tauri's `invoke` into that boundary. The Sources view
imports this wrapper only after the hidden-root gate exists; its empty-root
default state still keeps the action disabled.
`apps/desktop/src/commands/loadStorageSummaryClient.ts` is the thin runtime
wrapper for the read-only `load_storage_summary` command. Its startup helper
accepts only storage-summary payloads, keeps structured unavailable states
redacted, and converts thrown browser/Tauri failures into a generic unavailable
message so exception text cannot echo local paths.
The pure helper lives in `apps/desktop/src/commands/loadStorageSummaryStartup.ts`
so command tests can cover startup success and unavailable behavior without a
Tauri runtime import.
`apps/desktop/src/data/dashboard-summary.ts` normalizes a successful
`storage_summary` into the dashboard payload used by Daily and Weekly. It
completes the UI source map without displaying paths and marks
`openai_api_cost` as a secondary unavailable source so PR5 local refresh does
not reuse mock API cost values.
The Sources page also keeps successful `refresh_results` in memory for the
current session and renders a `Last Refresh` table with aggregate sync metadata
only: source, status, confidence, event count, and sync-run id.
The pure `buildRefreshSourcesManualArgs` helper converts camelCase UI drafts to
snake_case command args while omitting blank optional roots; it does not infer,
discover, read, or validate local paths.
The runtime Sources action derives `end_day_utc` from the current UTC day with
`manualRefreshEndDayUtc`; the fixed `2026-06-14` date is retained only for
deterministic command samples and fixture tests.
The separate `buildGatedRefreshSourcesManualArgs` helper is reserved for future
manual-refresh UI wiring: it requires both explicit Codex and Claude Code roots
before producing command args and returns the same structured
`invalid_refresh_request` payload when either root is missing.
The Sources setup rows live in the typed `explicitRootMockRows` fixture. They
keep Codex and Claude Code as the only disabled picker rows, preserve
label-only/no-path state, and keep Cursor, Gemini CLI, and GitHub Copilot as
status-only or official-report paths.
Rows separate their internal setup `state` from the visible `displayValue`, so a
selected root can render as a safe label such as `Selected, path hidden` without
printing a source root, filename, or local directory.
Typed `pathPolicyLabels` make those states visible in the mock Sources panel:
explicit roots show no path storage, Cursor and Gemini CLI show no local parser,
and GitHub Copilot stays official-report only.
Typed `nextStep` hints keep the next action explicit without wiring live sync:
Codex and Claude Code point to explicit-root setup, Cursor stays manual/status
only, Gemini CLI points to telemetry/export setup, and GitHub Copilot points to
official reports.
The pure `buildExplicitRootSetupRows` helper accepts transient Codex and Claude
Code root selections and produces path-free setup rows. This keeps selected-root
readiness separate from root display/storage and does not serialize supplied
root values into the Sources panel state.
`buildManualRefreshDraftFromHiddenRoots` composes those path-free rows with the
manual refresh readiness check. It exposes a trimmed command draft only when
both explicit roots and bridge wiring are ready; otherwise the draft stays
`null`.
The same fixture exposes `getManualRefreshReadiness`, which treats Codex's
`Selected (mock)` label as still missing a real explicit root and keeps the
manual refresh path blocked until both explicit roots and Tauri wiring exist.
It can also model the future disabled-to-enabled transition: only selected
Codex and Claude Code roots plus explicit Tauri wiring produce `canRun: true`.
The mock UI continues to use the default unwired state.
`npm run test:commands` verifies those desktop command contracts without Tauri:
strict args, command-name separation, success/error narrowing, and the static
sample totals. It also checks the production command invoker boundary plus the
mock source setup state for path redaction and source readiness labels.

The sample `apps/desktop/src-tauri/source-refresh-summary.sample.json` is shared
by the desktop TypeScript contract sample and the static Tauri command stub.
`apps/desktop/src/data/source-refresh-summary.sample.ts` exposes a typed import
without importing it into the UI runtime. Backend tests verify the JSON exactly
matches the generated PR5 fixture payload.

The error sample `apps/desktop/src-tauri/source-refresh-error.sample.json`
captures the deterministic `invalid_refresh_request` payload and is also
verified against the backend fixture. Desktop TypeScript imports both shared
samples for command contract tests, and Rust unit tests load both success and
error samples.

The Tauri command `source_refresh_summary_sample` returns the same static shape
for command registration checks. It embeds the shared JSON at build time. It is
not live sync and does not read local files.
The Rust crate also registers the production `refresh_sources_manual` command,
but it is gated: it requires explicit Codex and Claude Code roots before
spawning Python and returns structured `invalid_refresh_request` errors without
echoing supplied root values. The React UI now invokes it only through the
gated production client after hidden roots are ready.
Rust mirrors the manual refresh args as a snake_case
`RefreshSourcesManualArgs` struct with unknown fields denied.
The same Rust module mirrors the manual refresh result union as
`RefreshSourcesManualResult`, distinguishing aggregate success payloads from
structured `invalid_refresh_request` errors with the embedded static samples.
It also records the backend process module/stdin/stdout contract for
`backend.sources.refresh_command_cli`, with helpers for serializing manual
refresh args, invoking the backend process with synthetic fixture tests, and
parsing the success/error union. Rust can pass the internal
`YTH_REFRESH_DATABASE_PATH` process environment variable to the backend helper;
fixture tests prove a file-backed SQLite refresh can be read by a later backend
process without exposing the database path in stdout. The registered production
command resolves the default database path from Tauri's app-data directory and
uses the internal environment override only when it is set; React/Tauri request
args still cannot supply a database path. The command uses the gated process
helper and does not use
`source_refresh_summary_sample` as a live refresh fallback.
The Rust crate also registers a read-only `load_storage_summary` command that
uses the same internal app-data database path and returns the aggregate storage
summary shape without `refresh_results`. Missing persisted storage returns a
structured unavailable error instead of creating an empty database or silently
showing zero usage.

## Handoff Status

Ready for review:

- Backend core usage contracts, SQLite summary queries, and source sync registry
  are in place for Daily and rolling 7-day Weekly summaries.
- Codex and Claude Code aggregate JSONL adapters work with synthetic fixtures
  and explicit caller-provided roots.
- `build_primary_refresh_command_response_from_mapping` returns the future
  manual refresh success/error union without leaking validation exceptions.
- JSON bridge helpers return the same success/error union and redacted
  invalid-request payloads without creating a desktop live bridge.
- Backend stdin/stdout CLI bridge reuses the same JSON response boundary and
  stays redacted for future process-style Tauri wiring.
- The backend CLI can open a file-backed SQLite database through the internal
  `YTH_REFRESH_DATABASE_PATH` process environment variable. The JSON request
  payload still rejects `database_path`, and database-open failures return a
  redacted structured error without echoing the path.
- Desktop TypeScript mirrors `RefreshSourcesManualResult`, the manual refresh
  args, shared success/error command samples, and structured invalid-request
  errors. It also includes a production command invoker boundary that only calls
  `refresh_sources_manual` after gated args are available and redacts thrown
  browser/Tauri failures into a fixed unavailable state.
- The Tauri crate loads both static success and error samples, declares the
  manual refresh command name and the read-only persisted summary command name,
  mirrors the manual refresh and storage summary args/result unions, records the
  backend process module/stdin/stdout contracts, verifies process execution,
  Tauri app-data database path selection, file-backed database env handoff,
  persisted storage readback, and Rust-side gating with synthetic fixtures,
  registers `refresh_sources_manual` behind the Rust-side gate, registers
  `load_storage_summary` as read-only aggregate readback, and keeps
  `source_refresh_summary_sample` static.

Still blocked by setup:

- No enabled live desktop refresh UI in the empty-root default state.
- The Sources view can accept explicit roots through masked manual inputs, but
  no OS picker is opened. Visible `displayValue` labels stay path-free while
  typed next-step hints identify the setup action without rendering supplied
  roots, and browser autocomplete and spellcheck stay disabled.
  `buildExplicitRootSetupRows` can mark transient selections as selected for
  readiness without serializing root values into setup rows, and
  `buildManualRefreshDraftFromHiddenRoots` keeps those roots out of setup rows
  while preparing the command draft only after readiness is satisfied. The React
  Sources view consumes that hidden-root boundary with empty roots by default,
  so it renders missing-root readiness until a user supplies both roots.
- `applyExplicitRootSetupAction` models the future picker handoff as a pure
  hidden-root draft update: selecting a root trims the value for the command
  draft, clearing a root removes it, and the setup rows still serialize only
  path-free labels.
- The Sources view wires the manual refresh affordance to the production
  `refresh_sources_manual` client, but the empty-root default state is still
  blocked before invocation. Its mock state is centralized in a typed
  `manualRefreshMockState` with `canRun: false`. The separate readiness helper
  keeps label-only selected roots from counting as real explicit roots, and the
  panel can display tested path-free needs labels, dynamic root readiness, and
  tested bridge state without reading paths.
- The production Tauri `refresh_sources_manual` command is registered and React
  can invoke it only through the gated production client when hidden roots are
  ready.
- A successful gated refresh now promotes the returned aggregate
  `storage_summary` into the Daily and Weekly dashboard state and switches the
  shell badge to `Live local aggregate`.
- The React shell now calls the read-only `load_storage_summary` command on
  startup. Existing persisted storage promotes into the Daily and Weekly
  dashboard state; missing storage or browser/Tauri failures keep the mock
  summary visible instead of creating storage, showing zero usage, or exposing
  paths.
- The Sources view renders a path-free `Saved Aggregate` panel for startup
  readback state, showing readback status, dashboard source, and manual-only
  refresh posture.
- The Sources page shows the latest returned `refresh_results` as aggregate sync
  metadata, without source roots, local paths, filenames, or raw content.
- OpenAI API Cost remains secondary and unavailable after PR5 local refresh; the
  desktop does not reuse mock dollar values for live local summaries.
- No default local path scanning.
- No real local user directories are read without explicit roots.
- No Cursor, Gemini CLI, or GitHub Copilot local parser maturity is claimed
  beyond the documented status, manual, or official-report states.
- No OpenAI Admin/API cost sync in PR5.

## Implementation Status Matrix

| Area | Status | Notes |
| --- | --- | --- |
| Backend normalized event/storage contract | Ready | Daily and rolling 7-day Weekly summaries are fixture-tested. |
| Codex and Claude Code explicit-root sync | Ready | Synthetic aggregate JSONL fixtures cover the first parser path; no default path discovery. |
| Backend manual refresh response boundary | Ready | `build_primary_refresh_command_response_from_mapping` returns success or structured `invalid_refresh_request`. |
| Backend JSON bridge boundary | Ready | JSON args helpers return the same success/error union without echoing source roots. |
| Backend stdin/stdout bridge | Ready | `backend.sources.refresh_command_cli` wraps the JSON bridge for future process-style Tauri wiring; no default path discovery. |
| Backend file-backed refresh database boundary | Ready | `YTH_REFRESH_DATABASE_PATH` lets process tests open SQLite storage without accepting a database path in the JSON request payload or echoing the path in errors. |
| Desktop manual refresh args builder and invoker boundary | Ready | Pure TypeScript converts UI drafts to snake_case args, omits blank optional roots for setup-state requests, has a gated helper that requires both Codex and Claude Code roots before live refresh args are built, invokes only the registered production command when provided a Tauri invoke function, and redacts thrown invoke failures into a fixed unavailable state. |
| Rust/Tauri command-name, args, result, and process contract | Ready | `refresh_sources_manual` is registered behind the Rust-side explicit-root gate; snake_case args shape, success/error result union, Tauri app-data DB path selection, backend module args, stdin serialization, gated process invocation, optional file-backed DB env handoff, persisted `load_storage_summary` readback, and stdout parsing are tested with synthetic fixtures. |
| Static desktop sample command | Ready | `source_refresh_summary_sample` is registered and returns embedded aggregate JSON only. |
| Persisted summary readback command | Ready | `load_storage_summary` reads the same app-data SQLite aggregate by internal DB path only, returns storage summary payloads without refresh metadata, and reports missing storage as unavailable instead of zero usage. |
| Startup persisted-summary readback | Ready | React calls only the read-only `load_storage_summary` command on startup, promotes existing aggregate storage into Daily/Weekly, and falls back to mock data on unavailable or thrown failures without exposing paths. Sources also shows the path-free saved aggregate readback state. |
| Live desktop refresh action | Gated shell | Sources imports the production command client and calls only `refresh_sources_manual`, but the empty-root default keeps the button disabled until explicit Codex and Claude Code roots are present. |
| Manual refresh UI affordance | Gated UI | Sources shows the command name from typed `manualRefreshMockState`, tested path-free needs labels, dynamic root readiness, tested bridge state, running/success/failure states, and a disabled blocked state via `buildManualRefreshDraftFromHiddenRoots`. |
| Manual root entry shell | Gated UI | Typed `explicitRootMockRows`, masked manual inputs with browser autocomplete/spellcheck disabled, path-free `displayValue` labels, `buildExplicitRootSetupRows`, `buildManualRefreshDraftFromHiddenRoots`, `pathPolicyLabels`, and `nextStep` hints distinguish label-only, selected-explicit-root, no-local-parser, telemetry/export, and official-report states; no OS picker opens and no supplied root is rendered. |
| Refresh-to-dashboard handoff | Gated UI | Successful manual refresh normalizes `storage_summary` into Daily and Weekly dashboard state, labels the shell `Live local aggregate`, and keeps API cost unavailable instead of showing mock dollars. |
| Last refresh metadata | Gated UI | Sources renders returned `refresh_results` as source/status/confidence/events/sync-run metadata only, with event count and sync-run id formatted as metadata integers rather than token totals; no source roots, local paths, filenames, prompts, responses, request bodies, transcripts, tool output, or code snippets. |
| Cursor local parser | Status-only | Manual/status path until stable aggregate local data or official export is verified. |
| Gemini CLI local parser | Status-only | Setup-required until telemetry or export setup is verified. |
| GitHub Copilot local parser | Status-only | Official-report/manual path unless personal local token fields are verified. |
| OpenAI Admin/API cost sync | Out of PR5 | Reserved for PR6 as a secondary source. |

## Manual Refresh Promotion Checklist

Before React invokes the registered manual refresh command, the implementation
must satisfy all of these conditions:

- Refresh runs only after an explicit user action.
- Codex and Claude Code accept explicit user-selected roots; they do not infer
  default local paths silently.
- The command response remains aggregate-only and must not include prompt text,
  response text, request bodies, raw transcripts, tool output, code snippets,
  source roots, local paths, filenames, or local user directory names.
- Cursor remains manual/status-only until a stable aggregate local source or
  official export is verified.
- Gemini CLI remains setup-required until explicit telemetry or export setup is
  verified.
- GitHub Copilot remains official-report/manual unless personal local token
  fields are verified.
- Missing or unavailable allowance data is labeled unavailable, manual, or
  derived; it must not imply exact remaining usage.
- Missing or unavailable cost data must be labeled unavailable or partial; it
  must not be shown as zero cost.
- Daily and rolling 7-day Weekly remain the first-class summaries; Monthly stays
  out of the first live wiring path.
- `source_refresh_summary_sample` remains a static sample command. The
  production manual refresh command uses a separate command name.

## Live Wiring Readiness Gates

Before the user-visible action can become enabled and React can invoke the
registered `refresh_sources_manual` command, all gates below must be satisfied
in the same review:

- Explicit root selection exists for Codex and Claude Code, and selected labels
  still do not expose source roots, local paths, filenames, or local user
  directory names.
- The React action calls only the production `refresh_sources_manual` command;
  `source_refresh_summary_sample` remains static and unavailable as a live
  refresh fallback.
- The Tauri command returns the same success/error union as
  `build_primary_refresh_command_response_from_mapping` or the JSON bridge
  helpers, including structured `invalid_refresh_request` errors.
- The command never infers default local paths or enables auto-discovery fields.
- The response shown to React remains aggregate-only and passes the existing
  privacy scans for prompts, responses, request bodies, transcripts, tool
  output, code snippets, source roots, paths, filenames, and local user
  directory names.
- Cursor, Gemini CLI, and GitHub Copilot remain status-only, setup-required, or
  official-report paths unless separate fixture-backed parser evidence changes
  their source maturity.
- Daily and rolling 7-day Weekly summaries continue to be the only live refresh
  targets; Monthly remains out of the first wiring path.
- Desktop, backend, and Rust tests cover the disabled-to-enabled transition,
  root validation, no-path redaction, structured error payloads, and successful
  aggregate refresh.

## Non-Goals

- No ungated desktop live wiring, root persistence, or background sync yet.
- No background sync.
- No real local default path scanning.
- No account WebView login.
- No internal endpoint scraping.
- No OpenAI Admin API cost sync in this PR.
