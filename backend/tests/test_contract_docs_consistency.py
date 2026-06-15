from pathlib import Path

from backend.core import SOURCE_KINDS
from backend.sources import PRIMARY_REFRESH_COMMAND_NAME
from backend.storage.summary_command_cli import LOAD_STORAGE_SUMMARY_COMMAND_NAME


PR2_DOC = Path("docs/pr-2-parser-contract.md")
SOURCE_STRATEGY_DOC = Path("docs/source-strategy-v1.md")
PR5_DOC = Path("docs/pr-5-local-source-sync.md")
DESKTOP_APP = Path("apps/desktop/src/App.tsx")
DESKTOP_PACKAGE = Path("apps/desktop/package.json")
DESKTOP_README = Path("apps/desktop/README.md")
DESKTOP_REFRESH_ARGS = Path("apps/desktop/src/commands/refreshSourcesManualArgs.ts")
DESKTOP_REFRESH_ARGS_TEST = Path("apps/desktop/tests/refreshSourcesManualArgs.test.ts")
DESKTOP_SOURCE_SETUP_MOCK = Path("apps/desktop/src/data/source-setup.mock.ts")
DESKTOP_DASHBOARD_SUMMARY = Path("apps/desktop/src/data/dashboard-summary.ts")
DESKTOP_SOURCE_SETUP_MOCK_TEST = Path("apps/desktop/tests/sourceSetupMock.test.ts")
DESKTOP_DASHBOARD_SUMMARY_TEST = Path("apps/desktop/tests/dashboardSummary.test.ts")
DESKTOP_SOURCE_REFRESH_COMMANDS = Path("apps/desktop/src/commands/sourceRefreshSummary.ts")
DESKTOP_REFRESH_INVOKER = Path("apps/desktop/src/commands/refreshSourcesManualInvoker.ts")
DESKTOP_REFRESH_CLIENT = Path("apps/desktop/src/commands/refreshSourcesManualClient.ts")
DESKTOP_LOAD_STORAGE_SUMMARY_CLIENT = Path("apps/desktop/src/commands/loadStorageSummaryClient.ts")
DESKTOP_LOAD_STORAGE_SUMMARY_STARTUP = Path("apps/desktop/src/commands/loadStorageSummaryStartup.ts")
DESKTOP_SOURCE_REFRESH_COMMANDS_TEST = Path("apps/desktop/tests/sourceRefreshSummary.test.ts")
DESKTOP_REFRESH_INVOKER_TEST = Path("apps/desktop/tests/refreshSourcesManualInvoker.test.ts")
DESKTOP_SOURCE_REFRESH_ERROR_SAMPLE = Path(
    "apps/desktop/src/data/source-refresh-error.sample.ts"
)
DESKTOP_TAURI_LIB = Path("apps/desktop/src-tauri/src/lib.rs")
BACKEND_README = Path("backend/README.md")
BACKEND_REFRESH_COMMAND_CLI = Path("backend/sources/refresh_command_cli.py")
BACKEND_STORAGE_SUMMARY_COMMAND_CLI = Path("backend/storage/summary_command_cli.py")


def test_pr2_contract_doc_mentions_backend_source_kinds_and_mock_fixture():
    text = PR2_DOC.read_text(encoding="utf-8")

    for source_kind in SOURCE_KINDS:
        assert source_kind in text
    assert "backend/fixtures/mock_v1_summary.json" in text
    assert "openai_api_cost" in text
    assert "openai_api`" not in text


def test_source_strategy_uses_backend_source_kinds():
    text = SOURCE_STRATEGY_DOC.read_text(encoding="utf-8")

    for source_kind in SOURCE_KINDS:
        assert source_kind in text
    assert "openai_api`" not in text


def test_pr5_doc_keeps_manual_refresh_promotion_guardrails():
    text = PR5_DOC.read_text(encoding="utf-8")

    assert "Manual Refresh Promotion Checklist" in text
    assert "Live Wiring Readiness Gates" in text
    assert PRIMARY_REFRESH_COMMAND_NAME in text
    assert "`canRun: false`" in text
    assert "registered `refresh_sources_manual` command" in text
    assert "explicit user action" in text
    assert "user-selected/import roots" in text
    assert "Explicit root selection exists for at least one primary source" in text
    assert "selected labels" in text
    assert "aggregate-only" in text
    assert "must not include prompt text" in text
    assert "source roots, local paths, filenames" in text
    assert "source roots, paths, filenames" in text
    assert "Cursor support is limited to explicit usage-export import" in text
    assert "Gemini CLI support is limited to explicit telemetry/export import" in text
    assert "GitHub Copilot support is limited to explicit official metrics report import" in text
    assert "none may enable default local scanning or quota inference" in text
    assert "must not imply exact remaining usage" in text
    assert "must not be shown as zero cost" in text
    assert "Monthly stays" in text
    assert "Monthly remains out of the first wiring path" in text
    assert "source_refresh_summary_sample" in text
    assert "separate command name" in text
    assert "same success/error union" in text
    assert "invalid_refresh_request" in text
    assert "never infers default local paths" in text
    assert "auto-discovery fields" in text
    assert "disabled-to-enabled transition" in text
    assert "Synthetic Desktop Acceptance Smoke" in text
    assert "experiments/fixtures/local_sources/codex" in text
    assert "experiments/fixtures/local_sources/claude_code" in text
    assert "experiments/fixtures/local_sources/cursor" in text
    assert "experiments/fixtures/local_sources/gemini_cli" in text
    assert "experiments/fixtures/local_sources/github_copilot" in text
    assert "payload.info.last_token_usage" in text
    assert "message.usage" in text
    assert "Updated 17,040 aggregate tokens" in text
    assert "Restarting the desktop shell should load the saved aggregate" in text
    assert "explicit approval first" in text


def test_pr5_doc_records_handoff_status_without_claiming_ungated_live_wiring():
    text = PR5_DOC.read_text(encoding="utf-8")

    assert "Handoff Status" in text
    assert "Ready for review" in text
    assert "build_primary_refresh_command_response_from_mapping" in text
    assert "build_primary_refresh_command_response_from_json" in text
    assert "build_primary_refresh_command_response_json" in text
    assert "backend.sources.refresh_command_cli" in text
    assert "stdin/stdout" in text
    assert "JSON bridge helpers return the same success/error union" in text
    assert "Backend stdin/stdout CLI bridge" in text
    assert "RefreshSourcesManualResult" in text
    assert "source_refresh_summary_sample" in text
    assert "No enabled live desktop refresh UI in the empty-root default state" in text
    assert "disabled blocked state" in text
    assert "gated production client" in text
    assert "manualRefreshMockState" in text
    assert "`canRun: false`" in text
    assert f"The production Tauri `{PRIMARY_REFRESH_COMMAND_NAME}`" in text
    assert "React UI now invokes it only through" in text
    assert "No default local path scanning" in text
    assert "No real local user directories are read without explicit roots" in text
    assert "Cursor, Gemini CLI, and GitHub Copilot support only explicit usage import" in text
    assert "No OpenAI Admin/API cost sync in PR5" in text


def test_pr5_doc_records_implementation_status_matrix():
    text = PR5_DOC.read_text(encoding="utf-8")

    assert "Implementation Status Matrix" in text
    assert "| Backend normalized event/storage contract | Ready |" in text
    assert "| Primary source explicit-root sync | Ready |" in text
    assert "| Backend manual refresh response boundary | Ready |" in text
    assert "| Backend JSON bridge boundary | Ready |" in text
    assert "| Backend stdin/stdout bridge | Ready |" in text
    assert "| Desktop manual refresh args builder and invoker boundary | Ready |" in text
    assert "| Rust/Tauri command-name, args, result, and process contract | Ready |" in text
    assert "| Static desktop sample command | Ready |" in text
    assert "| Live desktop refresh action | Gated shell |" in text
    assert "| Manual refresh UI affordance | Gated UI |" in text
    assert "| Manual root entry shell | Gated UI |" in text
    assert "| Refresh-to-dashboard handoff | Gated UI |" in text
    assert "| Last refresh metadata | Gated UI |" in text
    assert "explicitRootMockRows" in text
    assert "| Cursor usage import | Ready |" in text
    assert "| Gemini CLI telemetry import | Ready |" in text
    assert "| GitHub Copilot official report import | Ready |" in text
    assert "| OpenAI Admin/API cost sync | Out of PR5 |" in text
    assert "empty-root default keeps the button disabled" in text
    assert "Live local aggregate" in text
    assert "keeps API cost unavailable instead of showing mock dollars" in text
    assert "source/status/confidence/events/sync-run metadata only" in text
    assert "no default path discovery" in text
    assert "selected explicit roots, usage-export import" in text
    assert "no OS picker opens and no supplied root is rendered" in text


def test_desktop_command_contract_matches_primary_refresh_request_shape():
    text = DESKTOP_SOURCE_REFRESH_COMMANDS.read_text(encoding="utf-8")
    args_text = DESKTOP_REFRESH_ARGS.read_text(encoding="utf-8")
    invoker_text = DESKTOP_REFRESH_INVOKER.read_text(encoding="utf-8")
    client_text = DESKTOP_REFRESH_CLIENT.read_text(encoding="utf-8")
    load_client_text = DESKTOP_LOAD_STORAGE_SUMMARY_CLIENT.read_text(encoding="utf-8")
    load_startup_text = DESKTOP_LOAD_STORAGE_SUMMARY_STARTUP.read_text(encoding="utf-8")
    args_test_text = DESKTOP_REFRESH_ARGS_TEST.read_text(encoding="utf-8")
    command_test_text = DESKTOP_SOURCE_REFRESH_COMMANDS_TEST.read_text(encoding="utf-8")
    invoker_test_text = DESKTOP_REFRESH_INVOKER_TEST.read_text(encoding="utf-8")
    error_sample_text = DESKTOP_SOURCE_REFRESH_ERROR_SAMPLE.read_text(encoding="utf-8")
    setup_text = DESKTOP_SOURCE_SETUP_MOCK.read_text(encoding="utf-8")
    dashboard_text = DESKTOP_DASHBOARD_SUMMARY.read_text(encoding="utf-8")
    setup_test_text = DESKTOP_SOURCE_SETUP_MOCK_TEST.read_text(encoding="utf-8")
    dashboard_test_text = DESKTOP_DASHBOARD_SUMMARY_TEST.read_text(encoding="utf-8")
    package_text = DESKTOP_PACKAGE.read_text(encoding="utf-8")
    readme_text = DESKTOP_README.read_text(encoding="utf-8")
    pr5_text = PR5_DOC.read_text(encoding="utf-8")

    assert PRIMARY_REFRESH_COMMAND_NAME in text
    assert LOAD_STORAGE_SUMMARY_COMMAND_NAME in text
    assert "RefreshSourcesManualArgs" in text
    assert "RefreshSourcesManualArgs" in args_text
    assert "RefreshSourcesManualDraft" in text
    assert "RefreshSourcesManualDraft" in args_text
    assert "RefreshCommandErrorPayload" in text
    assert "RefreshCommandErrorPayload" in args_text
    assert "RefreshSourcesManualResult" in text
    assert "LoadStorageSummaryArgs" in text
    assert "LoadStorageSummaryResult" in text
    assert "isStorageSummaryPayload" in text
    assert "buildRefreshSourcesManualArgs" in text
    assert "buildRefreshSourcesManualArgs" in args_text
    assert "buildRefreshSourcesManualArgs" in args_test_text
    assert "buildGatedRefreshSourcesManualArgs" in args_text
    assert "buildGatedRefreshSourcesManualArgs" in args_test_text
    assert "manualRefreshEndDayUtc" in args_text
    assert "manualRefreshEndDayUtc" in args_test_text
    assert "buildGatedRefreshSourcesManualArgs" in invoker_text
    assert "invokeRefreshSourcesManualWith" in invoker_text
    assert "RefreshSourcesManualInvokeOutcome" in invoker_text
    assert "REFRESH_SOURCES_MANUAL_COMMAND" in invoker_text
    assert "SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND" not in invoker_text
    assert "Manual refresh unavailable" in invoker_text
    assert "refresh_unavailable" in invoker_text
    assert "@tauri-apps/api/core" not in invoker_text
    assert "invokeRefreshSourcesManual" in client_text
    assert "@tauri-apps/api/core" in client_text
    assert "invokeRefreshSourcesManualWith(invoke, draft)" in client_text
    assert "invokeLoadStorageSummary" in load_client_text
    assert "loadStartupStorageSummaryWith" in load_client_text
    assert "loadStartupStorageSummary" in load_client_text
    assert "LOAD_STORAGE_SUMMARY_COMMAND" in load_client_text
    assert "@tauri-apps/api/core" in load_client_text
    assert "database_path" not in load_client_text
    assert "loadStartupStorageSummaryWith" in load_startup_text
    assert "isStorageSummaryPayload" in load_startup_text
    assert "Persisted summary unavailable" in load_startup_text
    assert "@tauri-apps/api/core" not in load_startup_text
    assert "database_path" not in load_startup_text
    assert "invokeRefreshSourcesManualWith" in invoker_test_text
    assert "REFRESH_SOURCES_MANUAL_COMMAND" in invoker_test_text
    assert "buildDashboardSummaryFromRefresh" in invoker_test_text
    assert "manualRefreshSuccessMessage" in invoker_test_text
    assert "gated refresh success should normalize into the dashboard aggregate total" in invoker_test_text
    assert "gated refresh success should produce the path-free success message" in invoker_test_text
    assert "SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND" in invoker_test_text
    assert "manual refresh must not invoke the static sample command" in invoker_test_text
    assert "invalid gated args must not call Tauri invoke" in invoker_test_text
    assert "thrown Tauri failures should return a structured unavailable state" in invoker_test_text
    assert "thrown Tauri failures must not reflect local paths or exception text" in invoker_test_text
    assert "C:/Users/example/secret/usage.sqlite" in invoker_test_text
    assert "sourceRefreshSummarySampleCommandContract" in command_test_text
    assert "refreshSourcesManualCommandContract" in command_test_text
    assert "refreshSourcesManualErrorCommandContract" in command_test_text
    assert "loadStorageSummaryCommandContract" in command_test_text
    assert "loadStartupStorageSummaryWith" in command_test_text
    assert "LOAD_STORAGE_SUMMARY_COMMAND" in command_test_text
    assert "storage summary load must stay separate" in command_test_text
    assert "storage summary readback result must not include refresh metadata" in command_test_text
    assert "startup storage readback should accept storage summary payloads" in command_test_text
    assert "startup unavailable outcome should not expose internal database fields" in command_test_text
    assert "thrown startup failures should not reflect local paths or exception text" in command_test_text
    assert "isRefreshCommandErrorPayload" in command_test_text
    assert "isSourceRefreshSummaryPayload" in command_test_text
    assert "source-refresh-error.sample.json" in error_sample_text
    assert "buildExplicitRootSetupRows" in setup_test_text
    assert "buildManualRefreshDraftFromHiddenRoots" in setup_text
    assert "buildManualRefreshDraftFromHiddenRoots" in setup_test_text
    assert "buildDashboardSummaryFromRefresh" in dashboard_text
    assert "buildDashboardSummaryFromRefresh" in dashboard_test_text
    assert "openai_api_cost" in dashboard_text
    assert "claude_api_cost" in dashboard_text
    assert "gemini_api_cost" in dashboard_text
    assert "deepseek_api_cost" in dashboard_text
    assert 'status: "secondary_source"' in dashboard_text
    assert 'confidence: "unavailable"' in dashboard_text
    assert "OpenAI API cost should stay secondary" in dashboard_test_text
    assert "HiddenRootManualRefreshState" in setup_text
    assert "HiddenRootManualRefreshDraft" in setup_text
    assert "ExplicitRootSelectionDraft" in setup_text
    assert "explicitRootMockRows" in setup_test_text
    assert "getManualRefreshReadiness" in setup_test_text
    assert "manualRefreshBridgeLabel" in setup_text
    assert "manualRefreshBridgeLabel" in setup_test_text
    assert "manualRefreshNeedsLabel" in setup_text
    assert "manualRefreshNeedsLabel" in setup_test_text
    assert "manualRefreshRootsLabel" in setup_text
    assert "manualRefreshRootsLabel" in setup_test_text
    assert "No roots selected" in setup_test_text
    assert "At least one import root" in setup_test_text
    assert "Codex, Claude Code" in setup_test_text
    assert "pathPolicyLabels" in setup_test_text
    assert "displayValue" in setup_test_text
    assert "nextStep" in setup_test_text
    assert "manualRefreshMockState" in setup_test_text
    assert "The Sources view imports this" in readme_text
    assert "wrapper only behind the hidden-root readiness gate" in readme_text
    assert "Manual refresh unavailable" in readme_text
    assert "exception text or local paths" in readme_text
    assert "On app startup" in readme_text
    assert "read-only `load_storage_summary` command" in readme_text
    assert "loadStorageSummaryStartup.ts" in readme_text
    assert "unavailable states" in readme_text
    assert "Saved Aggregate" in readme_text
    assert "checking, loaded, or unavailable" in readme_text
    assert "manual-or-auto" in readme_text
    assert "hidden-root readiness gate" in readme_text
    assert "empty-root default" in readme_text
    assert "buildExplicitRootSetupRows" in readme_text
    assert "buildManualRefreshDraftFromHiddenRoots" in readme_text
    assert "getManualRefreshReadiness" in readme_text
    assert "pathPolicyLabels" in readme_text
    assert "nextStep" in readme_text
    assert "mock source setup state" in pr5_text
    assert "buildExplicitRootSetupRows" in pr5_text
    assert "buildManualRefreshDraftFromHiddenRoots" in pr5_text
    assert "getManualRefreshReadiness" in pr5_text
    assert "pathPolicyLabels" in pr5_text
    assert "nextStep" in pr5_text
    assert "command-name separation" in readme_text
    assert "success/error result type guards" in readme_text
    assert "shared success/error samples" in readme_text
    assert "success/error narrowing" in pr5_text
    assert "Desktop TypeScript imports both shared" in pr5_text
    assert "refreshSourcesManualCommandContract" in text
    assert "refreshSourcesManualErrorCommandContract" in text
    assert "loadStorageSummaryCommandContract" in text
    assert "isRefreshCommandErrorPayload" in text
    assert "isSourceRefreshSummaryPayload" in text
    assert "invalid_refresh_request" in args_text
    assert "end_day_utc" in text
    assert "endDayUtc" in args_text
    assert "codex_jsonl_root" in args_text
    assert "codexJsonlRoot" in args_text
    assert "claude_code_jsonl_root" in args_text
    assert "claudeCodeJsonlRoot" in args_text
    assert "started_at" in args_text
    assert "startedAt" in args_text
    assert "Date.UTC" in args_text
    assert "auto_discover" not in text
    assert "auto_discover" not in args_text
    assert "invoke(" not in text
    assert "invoke(" not in args_text
    assert "@tauri-apps/api" not in text
    assert "@tauri-apps/api" not in args_text
    assert "Blank optional root" in readme_text
    assert "derives `end_day_utc` from the current UTC day" in readme_text
    assert "fixed `2026-06-14` date remains only" in readme_text
    assert "gated manual refresh args helper" in readme_text
    assert "does not infer, discover, or read local paths" in readme_text
    assert "npm run test:commands" in readme_text
    assert "test:commands" in package_text
    assert "refreshSourcesManualArgs.test.js" in package_text
    assert "sourceRefreshSummary.test.js" in package_text
    assert "refreshSourcesManualInvoker.test.js" in package_text
    assert "sourceSetupMock.test.js" in package_text
    assert "dashboardSummary.test.js" in package_text
    assert "buildRefreshSourcesManualArgs" in pr5_text
    assert "buildGatedRefreshSourcesManualArgs" in pr5_text
    assert "refreshSourcesManualInvoker.ts" in pr5_text
    assert "refreshSourcesManualClient.ts" in pr5_text
    assert "redacts thrown" in pr5_text
    assert "Manual refresh unavailable" in pr5_text
    assert "loadStorageSummaryClient.ts" in pr5_text
    assert "loadStorageSummaryStartup.ts" in pr5_text
    assert "Saved Aggregate" in pr5_text
    assert "path-free saved aggregate readback state" in pr5_text
    assert "dashboard-summary.ts" in pr5_text
    assert "manualRefreshEndDayUtc" in pr5_text
    assert "fixed `2026-06-14` date is retained only" in pr5_text
    assert "refresh-to-dashboard normalization" in readme_text
    assert "partial local-source summaries do not silently become API cost data" in readme_text
    assert "`Last Refresh` table" in readme_text
    assert "source, status, confidence, event count, and sync-run id" in readme_text
    assert "Synthetic PR5 desktop smoke" in readme_text
    assert "experiments/fixtures/local_sources/codex" in readme_text
    assert "experiments/fixtures/local_sources/claude_code" in readme_text
    assert "payload.info.last_token_usage" in readme_text
    assert "message.usage" in readme_text
    assert "Automation must request explicit approval before running this GUI smoke" in readme_text
    assert "Updated 9,820 aggregate tokens" in readme_text
    assert "load_storage_summary" in readme_text
    assert "invokes only `refresh_sources_manual`" in pr5_text
    assert "never falls back to `source_refresh_summary_sample`" in pr5_text
    assert "imports this wrapper only after the hidden-root gate exists" in pr5_text
    assert "its empty-root" in pr5_text
    assert "default state still keeps the action disabled" in pr5_text
    assert "trimmed command draft" in pr5_text
    assert "draft stays" in pr5_text
    assert "snake_case command args" in pr5_text
    assert "it does not infer" in pr5_text
    assert "discover, read, or validate local paths" in pr5_text


def test_backend_refresh_command_cli_is_redacted_stdin_stdout_boundary():
    cli_text = BACKEND_REFRESH_COMMAND_CLI.read_text(encoding="utf-8")
    readme_text = BACKEND_README.read_text(encoding="utf-8")
    pr5_text = PR5_DOC.read_text(encoding="utf-8")

    assert "run_primary_refresh_command_io" in cli_text
    assert "REFRESH_DATABASE_PATH_ENV_VAR" in cli_text
    assert "YTH_REFRESH_DATABASE_PATH" in cli_text
    assert "database_path=refresh_database_path_from_env()" in cli_text
    assert "build_primary_refresh_command_response_json" in cli_text
    assert "stdin.read()" in cli_text
    assert "stdout.write" in cli_text
    assert "discover_jsonl_sources" not in cli_text
    assert "auto_discover" not in cli_text
    assert "backend.sources.refresh_command_cli" in readme_text
    assert "stdin/stdout boundary" in readme_text
    assert "file-backed SQLite database" in readme_text
    assert "not accepted in the JSON request payload" in readme_text
    assert "`YTH_REFRESH_DATABASE_PATH`" in pr5_text
    assert "rejects `database_path`" in pr5_text
    assert "redacted structured error without echoing the path" in pr5_text
    assert "| Backend file-backed refresh database boundary | Ready |" in pr5_text
    assert "does not infer default source" in readme_text
    assert "echo supplied roots" in readme_text
    assert "process-style bridge wiring" in pr5_text
    assert "aggregate-only success/error union" in pr5_text


def test_backend_storage_summary_command_cli_is_readonly_readback_boundary():
    cli_text = BACKEND_STORAGE_SUMMARY_COMMAND_CLI.read_text(encoding="utf-8")
    readme_text = BACKEND_README.read_text(encoding="utf-8")
    pr5_text = PR5_DOC.read_text(encoding="utf-8")
    readme_flat = " ".join(readme_text.split())

    assert f'LOAD_STORAGE_SUMMARY_COMMAND_NAME = "{LOAD_STORAGE_SUMMARY_COMMAND_NAME}"' in cli_text
    assert 'LOAD_STORAGE_SUMMARY_DATABASE_PATH_ENV_VAR = "YTH_REFRESH_DATABASE_PATH"' in cli_text
    assert "run_load_storage_summary_command_io" in cli_text
    assert "build_load_storage_summary_response_json" in cli_text
    assert "build_storage_summary_payload" in cli_text
    assert "not path.is_file()" in cli_text
    assert "storage_summary_unavailable" in cli_text
    assert "connect_database(path)" in cli_text
    assert "initialize_schema" not in cli_text
    assert "refresh_results" not in cli_text
    assert "discover_jsonl_sources" not in cli_text
    assert "backend.storage.summary_command_cli" in readme_text
    assert "read an existing SQLite aggregate summary" in readme_text
    assert "without creating an empty database" in readme_flat
    assert "structured unavailable error instead of fake zero usage" in readme_flat
    assert "read-only `load_storage_summary` command" in pr5_text
    assert "without `refresh_results`" in pr5_text
    assert "structured unavailable error" in pr5_text
    assert "showing zero usage" in pr5_text
    assert "| Persisted summary readback command | Ready |" in pr5_text
    assert "| Startup persisted-summary readback | Ready |" in pr5_text
    assert "React calls only the read-only `load_storage_summary` command on startup" in pr5_text
    assert "Sources also shows the path-free saved aggregate readback state" in pr5_text


def test_desktop_mock_shell_keeps_sync_affordances_disabled():
    app_text = DESKTOP_APP.read_text(encoding="utf-8")
    dashboard_summary_text = DESKTOP_DASHBOARD_SUMMARY.read_text(encoding="utf-8")
    dashboard_summary_test_text = DESKTOP_DASHBOARD_SUMMARY_TEST.read_text(encoding="utf-8")
    setup_text = DESKTOP_SOURCE_SETUP_MOCK.read_text(encoding="utf-8")
    readme_text = DESKTOP_README.read_text(encoding="utf-8")
    pr5_text = Path("docs/pr-5-local-source-sync.md").read_text(encoding="utf-8")

    assert "Mock data" in dashboard_summary_text
    assert "Live local aggregate" in dashboard_summary_text
    assert "buildDashboardSummaryFromRefresh" in app_text
    assert "loadStartupStorageSummary" in app_text
    assert "StartupStorageStatus" in app_text
    assert "Saved Aggregate" in app_text
    assert "Saved aggregate readback state" in app_text
    assert "startupStorageStatusLabel" in app_text
    assert "startupStorageStatusLabel" in dashboard_summary_text
    assert "startupStorageStatusLabel({ phase: \"loading\" })" in dashboard_summary_test_text
    assert "Mock fallback" in app_text
    assert "Manual or auto" in app_text
    assert "dashboardQualityLabel" in app_text
    assert "dashboardQualityLabel" in dashboard_summary_text
    assert "dashboardQualityLabel(\"local_refresh\", { phase: \"loading\" })" in dashboard_summary_test_text
    assert "Loading saved aggregate" in dashboard_summary_text
    assert "setDashboardPayload" in app_text
    assert "setDashboardDataMode" in app_text
    assert "setLastRefreshResults" in app_text
    assert "setStartupStorageReadState" in app_text
    assert "handleRefreshSummary(outcome.result)" in app_text
    assert "cost_summary" in app_text
    assert "Stored Cost Breakdown" in app_text
    assert "No stored cost data" in app_text
    assert "personal API key" in app_text
    assert "secondary source not connected" not in app_text
    assert "ManualRefreshMock" in app_text
    assert "manualRefreshBridgeLabel" in app_text
    assert "manualRefreshNeedsLabel" in app_text
    assert "manualRefreshRootsLabel" in app_text
    assert "const bridgeLabel = manualRefreshBridgeLabel(readiness)" in app_text
    assert "const needsLabel = manualRefreshNeedsLabel(readiness)" in app_text
    assert "const rootsLabel = manualRefreshRootsLabel(readiness)" in app_text
    assert "No roots selected" in setup_text
    assert "LastRefreshResults" in app_text
    assert "Last Refresh" in app_text
    assert "Not run this session" in app_text
    assert "result.events_seen" in app_text
    assert "result.sync_run_id" in app_text
    assert "formatInteger(result.events_seen)" in app_text
    assert "formatInteger(result.sync_run_id)" in app_text
    assert "formatTokens(result.sync_run_id)" not in app_text
    assert "updateExplicitRoot" in app_text
    assert "clearExplicitRoot" in app_text
    assert "rootDraftValue" in app_text
    assert "type=\"password\"" in app_text
    assert "autoComplete=\"off\"" in app_text
    assert "spellCheck={false}" in app_text
    assert "Hidden root" in app_text
    assert "Clear ${sourceLabels[row.sourceKind]} hidden root" in app_text
    assert "root-entry" in app_text
    assert "root-input" in app_text
    assert "source-setup.mock.js" in app_text
    assert "type ManualRefreshUiState" in setup_text
    assert "type ManualRefreshReadiness" in setup_text
    assert "type ManualRefreshReadinessOptions" in setup_text
    assert "type ExplicitRootMockRow" in setup_text
    assert "manualRefreshMockState" in app_text
    assert "manualRefreshMockState" in setup_text
    assert "buildManualRefreshDraftFromHiddenRoots" in app_text
    assert "manualRefreshEndDayUtc()" in app_text
    assert "invokeRefreshSourcesManual" in app_text
    assert "isRefreshCommandErrorPayload" in app_text
    assert "manualRefreshBoundary.rows" in app_text
    assert "manualRefreshBoundary.readiness" in app_text
    assert "manualRefreshBoundary.canInvoke" in app_text
    assert "manualRefreshBoundary.draft" in app_text
    assert "explicitRootMockRows" in setup_text
    assert "getManualRefreshReadiness" in setup_text
    assert "buildExplicitRootSetupRows" in setup_text
    assert "buildManualRefreshDraftFromHiddenRoots" in setup_text
    assert "applyExplicitRootSetupAction" in setup_text
    assert 'type: "select_root"' in setup_text
    assert 'type: "clear_root"' in setup_text
    assert "root.trim()" in setup_text
    assert "delete next[field]" in setup_text
    assert "ExplicitRootSelectionDraft" in setup_text
    assert "hasTauriWiring?: boolean" in setup_text
    assert "pathPolicyLabels" in app_text
    assert "pathPolicyLabels" in setup_text
    assert "row.displayValue" in app_text
    assert "row.nextStep" in app_text
    assert "displayValue" in setup_text
    assert "nextStep" in setup_text
    assert "missingRootLabels" not in app_text
    assert "readiness.configuredExplicitRoots" in setup_text
    assert "readiness.hasTauriWiring" in setup_text
    assert "canInvoke" in app_text
    assert "const canRun = hasTauriWiring && configuredExplicitRoots.length > 0" in setup_text
    assert "blockedReason: canRun ? null : manualRefreshMockState.blockedReason" in setup_text
    assert "canRun: false" in setup_text
    assert 'blockedReason: "explicit_roots_and_tauri_wiring"' in setup_text
    assert "Manual Refresh" in app_text
    assert "Manual refresh state" in app_text
    assert "ManualRefreshMock" in app_text
    assert "RefreshSummaryItem" in app_text
    assert 'label="Ready check"' in app_text
    assert "detail={bridgeLabel}" in app_text
    assert "StatePanel" not in app_text
    assert "First Launch" not in app_text
    assert "No Local Sources" not in app_text
    assert "{ hasTauriWiring: true }" in app_text
    assert "handleManualRefresh" in app_text
    assert "manualRefreshStatusLabel" in app_text
    assert "manualRefreshStatusLabel" in setup_text
    assert "manualRefreshSuccessMessage" in app_text
    assert "manualRefreshSuccessMessage" in setup_text
    assert "loadSourceRootPreferences" in app_text
    assert "saveSourceRootPreferences" in app_text
    assert "clearSourceRootPreferences" in app_text
    assert "sourceRootStorageLabel" in app_text
    assert "shouldRunAutoRefresh" in app_text
    assert "setInterval" in app_text
    assert "Save roots" in app_text
    assert "Forget" in app_text
    assert "Saved locally" in Path("apps/desktop/src/commands/sourceRootPreferences.ts").read_text(encoding="utf-8")
    assert "Needs saved roots" in Path("apps/desktop/src/commands/sourceRootPreferences.ts").read_text(encoding="utf-8")
    assert "ManualRefreshRunState" in setup_text
    assert "manualRefreshStatusLabel(true, { phase: \"running\" })" in DESKTOP_SOURCE_SETUP_MOCK_TEST.read_text(encoding="utf-8")
    assert "Updated 7,570 aggregate tokens" in DESKTOP_SOURCE_SETUP_MOCK_TEST.read_text(encoding="utf-8")
    assert "manualRefreshSuccessMessage(payload.summary.totals.total_tokens)" in app_text
    assert "latest manual refresh aggregate" in app_text
    assert "refresh_sources_manual" in setup_text
    assert "Partial mock" not in setup_text
    assert "Blocked" in setup_text
    assert "Manual refresh is disabled until at least one explicit root and Tauri wiring are ready" in setup_text
    assert "Add at least one hidden source root" in setup_text
    assert "disabled={!canInvoke || isRunning}" in app_text
    assert 'aria-label={canInvoke ? "Run manual refresh" : manualRefreshMockState.disabledAriaLabel}' in app_text
    assert 'title={canInvoke ? "Run production manual refresh" : manualRefreshMockState.disabledTitle}' in app_text
    assert "ExplicitRootsMock" in app_text
    assert "Explicit Roots" in app_text
    assert 'picker: "codex"' in setup_text
    assert 'picker: "claude_code"' in setup_text
    assert 'picker: "gemini_cli"' in setup_text
    assert 'picker: "cursor"' not in setup_text
    assert 'picker: "github_copilot"' not in setup_text
    assert "Selected (mock)" in setup_text
    assert "Selected, path hidden" in setup_text
    assert "Hidden root selected" in setup_text
    assert 'rootReadiness: "label_only"' not in setup_text
    assert "selected_explicit_root" in setup_text
    assert "Not selected" in setup_text
    assert "No root selected" in setup_text
    assert "Explicit root required" in setup_text
    assert 'rootReadiness: "missing_explicit_root"' in setup_text
    assert 'pickerAction: hasExplicitRoot ? "Change" : "Choose"' in setup_text
    assert 'pickerAction: "Choose"' in setup_text
    assert 'pathPolicy: "no_path_stored"' in setup_text
    assert 'pathPolicy: "no_local_parser"' not in setup_text
    assert 'pathPolicy: "official_report_import"' not in setup_text
    assert "Path hidden" in setup_text
    assert "No local parser" not in setup_text
    assert "Official report import" not in setup_text
    assert "Choose explicit root" in setup_text
    assert "Choose usage export" not in setup_text
    assert "Choose telemetry export" in setup_text
    assert "Choose official report" not in setup_text
    assert "Ready for refresh" in setup_text
    assert "label={pathPolicyLabels[row.pathPolicy]}" in app_text
    assert "onRootChange(row.sourceKind, event.currentTarget.value)" in app_text
    assert "onClearRoot(row.sourceKind)" in app_text
    assert "Status only" not in setup_text
    assert "Official report root" not in setup_text
    assert "headerRefreshButtonLabel" in app_text
    assert "headerRefreshButtonTitle" in app_text
    assert "canRunHeaderRefresh" in app_text
    assert "handleHeaderRefresh" in app_text
    assert "disabled={!headerCanRefresh}" in app_text
    assert "onClick={handleHeaderRefresh}" in app_text
    assert "Refresh local aggregate" in app_text
    assert "Save roots before using header refresh" in Path("apps/desktop/src/commands/sourceRootPreferences.ts").read_text(encoding="utf-8")
    assert "showOpenDialog" not in app_text
    assert "invoke(" not in app_text
    assert "@tauri-apps/api" not in app_text
    assert "The header `Refresh` button is a shortcut" in readme_text
    assert "requires saved roots" in readme_text
    assert "| Header refresh shortcut | Gated UI |" in pr5_text
    assert "refresh action disabled" in readme_text
    assert "production command client" in readme_text
    assert "names `refresh_sources_manual`" in readme_text
    assert "`Path hidden`" in readme_text
    assert "`Official report import`" not in readme_text
    assert "typed `nextStep` hints" in readme_text
    assert "telemetry/export import" in readme_text
    assert "official report import" not in readme_text
    assert "any selected explicit import root plus Tauri wiring" in readme_text
    assert "tested path-free needs label" in readme_text
    assert "root readiness" in readme_text
    assert "tested bridge state" in readme_text
    assert "consumes that hidden-root boundary with empty roots" in readme_text
    pr5_text = PR5_DOC.read_text(encoding="utf-8")
    assert "The React" in pr5_text
    assert "Sources view consumes that hidden-root boundary" in pr5_text
    assert "tested path-free needs labels" in pr5_text
    assert "dynamic root readiness" in pr5_text
    assert "tested bridge state" in pr5_text
    assert "masked manual inputs" in readme_text
    assert "browser autocomplete and spellcheck disabled" in readme_text
    assert "metadata integers, not token totals" in readme_text
    assert "visible setup rows continue to show path-free labels" in readme_text
    assert "pure picker/manual-entry boundary" in readme_text
    assert "setup rows still render path-free labels" in readme_text
    assert "picker handoff" in PR5_DOC.read_text(encoding="utf-8")
    assert "setup rows still serialize only" in PR5_DOC.read_text(encoding="utf-8")
    assert "refresh action disabled" in readme_text
    assert "or read local" in readme_text
    assert "typed `manualRefreshMockState`" in readme_text
    assert "typed `explicitRootMockRows`" in readme_text
    assert "`canRun: false`" in readme_text
    assert "explicit-root setup rows" in readme_text
    assert "visible `displayValue` is a safe label" in readme_text
    assert "`Selected, path hidden` or `No root selected`" in readme_text
    assert "neither state displays" in readme_text
    assert "Save roots" in readme_text
    assert "Forget" in readme_text
    assert "Auto refresh stays disabled until at least one root is ready and saved" in readme_text
    assert "masked manual inputs" in PR5_DOC.read_text(encoding="utf-8")
    assert "browser autocomplete and spellcheck stay disabled" in PR5_DOC.read_text(encoding="utf-8")
    assert "no OS picker opens" in PR5_DOC.read_text(encoding="utf-8")
    assert "no supplied root is rendered" in PR5_DOC.read_text(encoding="utf-8")
    assert "metadata integers rather than token totals" in PR5_DOC.read_text(encoding="utf-8")


def test_tauri_registers_static_sample_and_gated_manual_refresh_command():
    rust_text = DESKTOP_TAURI_LIB.read_text(encoding="utf-8")
    readme_text = DESKTOP_README.read_text(encoding="utf-8")
    pr5_text = PR5_DOC.read_text(encoding="utf-8")
    pr5_flat = " ".join(pr5_text.split())

    assert 'SOURCE_REFRESH_SUMMARY_SAMPLE_COMMAND: &str = "source_refresh_summary_sample"' in rust_text
    assert f'REFRESH_SOURCES_MANUAL_COMMAND: &str = "{PRIMARY_REFRESH_COMMAND_NAME}"' in rust_text
    assert f'LOAD_STORAGE_SUMMARY_COMMAND: &str = "{LOAD_STORAGE_SUMMARY_COMMAND_NAME}"' in rust_text
    assert 'LOAD_SAVED_SOURCE_ROOTS_COMMAND: &str = "load_saved_source_roots"' in rust_text
    assert 'SAVE_SOURCE_ROOTS_COMMAND: &str = "save_source_roots"' in rust_text
    assert 'CLEAR_SAVED_SOURCE_ROOTS_COMMAND: &str = "clear_saved_source_roots"' in rust_text
    assert 'SOURCE_ROOTS_FILE_NAME: &str = "source-roots.json"' in rust_text
    assert "DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES" in rust_text
    assert "pub struct RefreshSourcesManualArgs" in rust_text
    assert "pub struct SavedSourceRoots" in rust_text
    assert "normalize_saved_source_roots" in rust_text
    assert "load_saved_source_roots_from_path" in rust_text
    assert "save_source_roots_to_path" in rust_text
    assert "clear_saved_source_roots_at_path" in rust_text
    assert "source_roots_path_from_app_data_dir" in rust_text
    assert 'BACKEND_REFRESH_COMMAND_MODULE: &str = "backend.sources.refresh_command_cli"' in rust_text
    assert 'BACKEND_LOAD_STORAGE_SUMMARY_COMMAND_MODULE: &str =' in rust_text
    assert '"backend.storage.summary_command_cli"' in rust_text
    assert "backend_refresh_process_module_args" in rust_text
    assert "backend_load_storage_summary_process_module_args" in rust_text
    assert "refresh_sources_manual_stdin" in rust_text
    assert "refresh_sources_manual_result_from_stdout" in rust_text
    assert "pub struct LoadStorageSummaryArgs" in rust_text
    assert "pub enum LoadStorageSummaryResult" in rust_text
    assert "load_storage_summary_stdin" in rust_text
    assert "load_storage_summary_result_from_stdout" in rust_text
    assert "run_refresh_sources_manual_backend_process" in rust_text
    assert "run_refresh_sources_manual_backend_process_with_database_path" in rust_text
    assert "run_load_storage_summary_backend_process_with_database_path" in rust_text
    assert "run_gated_refresh_sources_manual_backend_process" in rust_text
    assert "run_gated_refresh_sources_manual_backend_process_with_database_path" in rust_text
    assert "REFRESH_DATABASE_PATH_ENV_VAR" in rust_text
    assert 'REFRESH_DATABASE_PATH_ENV_VAR: &str = "YTH_REFRESH_DATABASE_PATH"' in rust_text
    assert 'REFRESH_DATABASE_FILE_NAME: &str = "usage.sqlite"' in rust_text
    assert ".env(REFRESH_DATABASE_PATH_ENV_VAR, path)" in rust_text
    assert "use tauri::Manager;" in rust_text
    assert "fn invalid_refresh_request" in rust_text
    assert "#[serde(deny_unknown_fields)]" in rust_text
    assert "pub end_day_utc: String" in rust_text
    assert "pub codex_jsonl_root: Option<String>" in rust_text
    assert "pub claude_code_jsonl_root: Option<String>" in rust_text
    assert "pub started_at: Option<String>" in rust_text
    assert "pub enum RefreshSourcesManualResult" in rust_text
    assert "Error(RefreshCommandErrorPayload)" in rust_text
    assert "Success(Value)" in rust_text
    assert "pub struct RefreshCommandErrorPayload" in rust_text
    assert "pub struct RefreshCommandError" in rust_text
    assert "refresh_sources_manual_result_accepts_success_payload" in rust_text
    assert "refresh_sources_manual_result_accepts_structured_error_payload" in rust_text
    assert "refresh_sources_manual_stdin_serializes_only_explicit_args" in rust_text
    assert "refresh_sources_manual_result_parses_success_stdout" in rust_text
    assert "refresh_sources_manual_result_parses_structured_error_stdout" in rust_text
    assert "load_storage_summary_result_parses_success_stdout" in rust_text
    assert "load_storage_summary_result_parses_structured_error_stdout" in rust_text
    assert "load_storage_summary_stdin_serializes_only_end_day" in rust_text
    assert "load_storage_summary_args_reject_database_path_fields" in rust_text
    assert "refresh_sources_manual_backend_process_returns_fixture_success" in rust_text
    assert "refresh_sources_manual_backend_process_uses_file_backed_database_path" in rust_text
    assert "load_storage_summary_backend_process_missing_database_is_unavailable" in rust_text
    assert "load_storage_summary_command_reads_file_backed_refresh_database" in rust_text
    assert "refresh_database_path_prefers_env_override_before_app_data_default" in rust_text
    assert "source_roots_path_uses_app_data_config_file" in rust_text
    assert "saved_source_roots_normalize_roots_and_auto_refresh_gate" in rust_text
    assert "saved_source_roots_file_round_trips_without_path_echo_errors" in rust_text
    assert "saved_source_roots_invalid_file_returns_redacted_error" in rust_text
    assert "refresh_sources_manual_backend_process_returns_redacted_error" in rust_text
    assert "gated_refresh_sources_manual_backend_process_requires_one_root" in rust_text
    assert "gated_refresh_sources_manual_backend_process_rejects_before_database_setup" in rust_text
    assert "gated_refresh_sources_manual_backend_process_accepts_single_codex_root" in rust_text
    assert "gated_refresh_sources_manual_backend_process_returns_fixture_success" in rust_text
    assert "refresh_sources_manual_command_requires_one_root" in rust_text
    assert "refresh_sources_manual_command_returns_fixture_success" in rust_text
    assert "fn refresh_sources_manual(" in rust_text
    assert "app: tauri::AppHandle" in rust_text
    assert "refresh_sources_manual_command" in rust_text
    assert "fn load_storage_summary(" in rust_text
    assert "load_storage_summary_command" in rust_text
    assert "runtime_python_executable" in rust_text
    assert "runtime_workspace_root" in rust_text
    assert "runtime_refresh_database_path" in rust_text
    assert "let refresh_database_path = runtime_refresh_database_path(&app)?;" in rust_text
    assert ".app_data_dir()" in rust_text
    assert "refresh_database_path_from_env_or_app_data_dir" in rust_text
    assert "refresh_database_path_from_app_data_dir" in rust_text
    assert "at least one source root is required for manual refresh" in rust_text
    assert "auto_discover" in rust_text
    assert "Command::new" in rust_text
    assert ".args(backend_refresh_process_module_args())" in rust_text
    assert ".args(backend_load_storage_summary_process_module_args())" in rust_text
    assert ".stdin(Stdio::piped())" in rust_text
    assert ".stdout(Stdio::piped())" in rust_text
    assert ".stderr(Stdio::piped())" in rust_text
    assert "failed to start backend refresh process" in rust_text
    assert "path_text(&database_path)" in rust_text
    assert "!text.contains(REFRESH_DATABASE_PATH_ENV_VAR)" in rust_text

    handler_start = rust_text.index("tauri::generate_handler![")
    handler_end = rust_text.index("]", handler_start)
    registered_commands = rust_text[handler_start:handler_end]

    assert "source_refresh_summary_sample" in registered_commands
    assert PRIMARY_REFRESH_COMMAND_NAME in registered_commands
    assert LOAD_STORAGE_SUMMARY_COMMAND_NAME in registered_commands
    assert "load_saved_source_roots" in registered_commands
    assert "save_source_roots" in registered_commands
    assert "clear_saved_source_roots" in registered_commands
    assert "REFRESH_SOURCES_MANUAL_COMMAND" not in registered_commands
    assert "LOAD_STORAGE_SUMMARY_COMMAND" not in registered_commands
    assert "registers the production `refresh_sources_manual` command" in readme_text
    assert "the command is gated" in readme_text
    assert "mirrors the manual refresh args" in readme_text
    assert "mirrors the manual refresh result union" in readme_text
    assert "backend.sources.refresh_command_cli" in readme_text
    assert "backend process" in readme_text
    assert "Rust process tests pass that environment variable" in readme_text
    assert "without echoing the database path" in readme_text
    assert "Rust resolves the default refresh database path from Tauri's app-data" in readme_text
    assert "env var remains an internal" in readme_text
    assert "before spawning the backend process" in readme_text
    assert "synthetic fixture tests" in readme_text
    assert "do not call the static sample command" in readme_text
    assert "as a live fallback" in readme_text
    assert "RefreshSourcesManualResult" in readme_text
    assert "structured `invalid_refresh_request` errors" in readme_text
    assert "read-only `load_storage_summary` command" in readme_text
    assert "`load_saved_source_roots`, `save_source_roots`, and" in readme_text
    assert "returns only the aggregate storage" in readme_text
    assert "showing fake zero usage" in readme_text
    assert "unknown fields denied" in readme_text
    assert "registers the production `refresh_sources_manual` command" in pr5_text
    assert "React UI now invokes it only through" in pr5_text
    assert "Rust mirrors the manual refresh args" in pr5_text
    assert "mirrors the manual refresh result union" in pr5_text
    assert "backend process module/stdin/stdout contract" in pr5_text
    assert "file-backed SQLite refresh can be read by a later backend" in pr5_text
    assert "without exposing the database path in stdout" in pr5_text
    assert "resolves the default database path from Tauri's app-data directory" in pr5_text
    assert "args still cannot supply a database path" in pr5_text
    assert "process invocation" in pr5_text
    assert "synthetic fixtures" in pr5_text
    assert "success/error result union" in pr5_text
    assert "React invokes the registered manual refresh command" in pr5_text
    assert "registered `refresh_sources_manual` command" in pr5_text
    assert "registers `load_storage_summary` as read-only aggregate readback" in pr5_flat
    assert "Explicit-root config commands" in pr5_text
    assert "`load_saved_source_roots`, `save_source_roots`, and" in pr5_text
    assert "Persisted summary readback command" in pr5_text
