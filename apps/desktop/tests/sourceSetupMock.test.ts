import {
  applyExplicitRootSetupAction,
  buildExplicitRootSetupRows,
  buildManualRefreshDraftFromHiddenRoots,
  explicitRootMockRows,
  getManualRefreshReadiness,
  manualRefreshBridgeLabel,
  manualRefreshMockState,
  manualRefreshNeedsLabel,
  manualRefreshRootsLabel,
  manualRefreshStatusLabel,
  manualRefreshSuccessMessage,
  pathPolicyLabels
} from "../src/data/source-setup.mock.js";

assert(
  manualRefreshMockState.commandName === "refresh_sources_manual",
  "manual refresh mock state should name the future command"
);
assert(!manualRefreshMockState.canRun, "manual refresh must stay disabled in mock mode");
assert(
  manualRefreshMockState.blockedReason === "explicit_roots_and_tauri_wiring",
  "manual refresh should stay blocked on explicit roots and Tauri wiring"
);

assert(explicitRootMockRows.length === 5, "all primary local setup sources should be represented");
assertDeepEqual(
  explicitRootMockRows.map((row) => row.sourceKind),
  ["codex", "claude_code", "cursor", "gemini_cli", "github_copilot"]
);
assertDeepEqual(
  explicitRootMockRows.filter((row) => row.picker).map((row) => row.sourceKind),
  ["codex", "claude_code"]
);

const codex = explicitRootMockRows.find((row) => row.sourceKind === "codex");
const claudeCode = explicitRootMockRows.find((row) => row.sourceKind === "claude_code");
const cursor = explicitRootMockRows.find((row) => row.sourceKind === "cursor");
const geminiCli = explicitRootMockRows.find((row) => row.sourceKind === "gemini_cli");
const githubCopilot = explicitRootMockRows.find((row) => row.sourceKind === "github_copilot");

assert(codex?.state === "Selected (mock)", "Codex should show label-only selected mock state");
assert(codex.displayValue === "Selected, path hidden", "Codex should hide the selected root path");
assert(codex.pathPolicy === "no_path_stored", "Codex mock state must hide path display");
assert(codex.rootReadiness === "label_only", "Codex label-only state should not count as a real root");
assert(codex.nextStep === "Needs explicit root", "Codex selected mock label should still need setup");
assert(claudeCode?.state === "Not selected", "Claude Code should still require explicit setup");
assert(claudeCode.displayValue === "No root selected", "Claude Code should not display a path placeholder");
assert(claudeCode.pathPolicy === "no_path_stored", "Claude Code mock state must hide path display");
assert(
  claudeCode.rootReadiness === "missing_explicit_root",
  "Claude Code should still be missing an explicit root"
);
assert(claudeCode.nextStep === "Choose explicit root", "Claude Code should guide explicit root setup");
assert(cursor?.pathPolicy === "no_local_parser", "Cursor should stay status/manual only");
assert(cursor.displayValue === "Manual status", "Cursor should show status only");
assert(cursor.nextStep === "Manual status only", "Cursor should stay manual/status only");
assert(geminiCli?.pathPolicy === "no_local_parser", "Gemini CLI should stay setup/status only");
assert(geminiCli.displayValue === "Telemetry/export setup", "Gemini CLI should show setup state only");
assert(
  geminiCli.nextStep === "Configure telemetry or export",
  "Gemini CLI should require telemetry/export setup"
);
assert(
  githubCopilot?.pathPolicy === "official_report_only",
  "GitHub Copilot should stay official-report only"
);
assert(githubCopilot.displayValue === "Official report", "Copilot should show report-only state");
assert(githubCopilot.nextStep === "Use official report", "Copilot should guide official report usage");
assert(pathPolicyLabels.no_path_stored === "Path hidden", "explicit roots should keep root values hidden");
assert(pathPolicyLabels.no_local_parser === "No local parser", "status-only tools should not imply parser maturity");
assert(pathPolicyLabels.official_report_only === "Official report", "Copilot should stay report-only");

const readiness = getManualRefreshReadiness();
assert(!readiness.canRun, "mock readiness must not enable manual refresh");
assert(!readiness.hasTauriWiring, "mock readiness must not claim Tauri wiring");
assertDeepEqual(
  readiness.missingExplicitRoots,
  ["codex", "claude_code"]
);
assert(
  manualRefreshRootsLabel(readiness) === "Missing Codex, Claude Code",
  "root readiness label should name only missing explicit roots"
);
assert(
  manualRefreshNeedsLabel(readiness) === "Codex, Claude Code",
  "needs label should list missing explicit roots without path values"
);
assert(manualRefreshBridgeLabel(readiness) === "not wired", "default bridge label should stay unwired");
assert(
  readiness.blockedReason === "explicit_roots_and_tauri_wiring",
  "readiness should reuse the mock blocked reason"
);
assert(
  manualRefreshStatusLabel(false, { phase: "idle" }) === "Blocked",
  "idle blocked state should reuse the typed mock label"
);
assert(
  manualRefreshStatusLabel(true, { phase: "idle" }) === "Ready",
  "idle invokable state should show ready"
);
assert(
  manualRefreshStatusLabel(true, { phase: "running" }) === "Running",
  "running state should override readiness"
);
assert(
  manualRefreshStatusLabel(false, { phase: "succeeded", message: "done" }) === "Succeeded",
  "success state should override blocked readiness"
);
assert(
  manualRefreshStatusLabel(true, { phase: "failed", message: "failed" }) === "Failed",
  "failure state should override invokable readiness"
);
assert(
  manualRefreshSuccessMessage(7570) === "Updated 7,570 aggregate tokens",
  "success message should format only the aggregate token total"
);
assert(
  !manualRefreshSuccessMessage(7570).includes("C:/Users"),
  "success message must not expose local paths"
);

const selectedRows = buildExplicitRootSetupRows({
  codexJsonlRoot: "synthetic/codex",
  claudeCodeJsonlRoot: "synthetic/claude-code"
});
const selectedCodex = selectedRows.find((row) => row.sourceKind === "codex");
const selectedClaudeCode = selectedRows.find((row) => row.sourceKind === "claude_code");
assert(selectedCodex?.displayValue === "Selected, path hidden", "selected Codex root should stay hidden");
assert(
  selectedCodex.rootReadiness === "selected_explicit_root",
  "selected Codex root should count as explicit"
);
assert(
  selectedClaudeCode?.rootReadiness === "selected_explicit_root",
  "selected Claude Code root should count as explicit"
);
assert(
  selectedClaudeCode.nextStep === "Ready for gated refresh",
  "selected roots should move only to gated refresh readiness"
);
assert(selectedCodex.detail === "Hidden root selected", "selected root details should stay path-free");

const selectedReadiness = getManualRefreshReadiness(selectedRows);
assertDeepEqual(selectedReadiness.missingExplicitRoots, []);
assert(manualRefreshRootsLabel(selectedReadiness) === "Ready", "selected roots should show ready root state");
assert(manualRefreshNeedsLabel(selectedReadiness) === "None", "selected roots should show no missing setup needs");
assert(!selectedReadiness.canRun, "selected roots should not enable refresh without Tauri wiring");
assert(!selectedReadiness.hasTauriWiring, "selected roots should not claim bridge wiring");
assert(
  selectedReadiness.blockedReason === "explicit_roots_and_tauri_wiring",
  "selected roots should stay blocked until bridge wiring exists"
);

const wiredReadiness = getManualRefreshReadiness(selectedRows, { hasTauriWiring: true });
assert(wiredReadiness.canRun, "selected roots plus bridge wiring should pass readiness");
assert(wiredReadiness.hasTauriWiring, "wired readiness should record the bridge state");
assert(manualRefreshBridgeLabel(wiredReadiness) === "wired", "wired bridge label should be explicit");
assertDeepEqual(wiredReadiness.missingExplicitRoots, []);
assert(wiredReadiness.blockedReason === null, "ready state should not keep a blocked reason");

const wiredLabelOnlyReadiness = getManualRefreshReadiness(explicitRootMockRows, { hasTauriWiring: true });
assert(!wiredLabelOnlyReadiness.canRun, "bridge wiring alone should not enable label-only roots");
assertDeepEqual(
  wiredLabelOnlyReadiness.missingExplicitRoots,
  ["codex", "claude_code"]
);

const actionDraft = applyExplicitRootSetupAction(
  applyExplicitRootSetupAction({}, { type: "select_root", sourceKind: "codex", root: " synthetic/codex " }),
  { type: "select_root", sourceKind: "claude_code", root: " synthetic/claude-code " }
);
assertDeepEqual(actionDraft, {
  codexJsonlRoot: "synthetic/codex",
  claudeCodeJsonlRoot: "synthetic/claude-code"
});
assert(
  !JSON.stringify(buildExplicitRootSetupRows(actionDraft)).includes("synthetic/codex"),
  "action-selected Codex root must not serialize into setup rows"
);
assert(
  !JSON.stringify(buildExplicitRootSetupRows(actionDraft)).includes("synthetic/claude-code"),
  "action-selected Claude Code root must not serialize into setup rows"
);

const clearedActionDraft = applyExplicitRootSetupAction(actionDraft, {
  type: "clear_root",
  sourceKind: "codex"
});
assertDeepEqual(clearedActionDraft, {
  claudeCodeJsonlRoot: "synthetic/claude-code"
});

const hiddenRootRefresh = buildManualRefreshDraftFromHiddenRoots(
  {
    endDayUtc: " 2026-06-14 ",
    codexJsonlRoot: " synthetic/codex ",
    claudeCodeJsonlRoot: " synthetic/claude-code ",
    startedAt: " 2026-06-14T00:00:00Z "
  },
  { hasTauriWiring: true }
);

assert(hiddenRootRefresh.canInvoke, "hidden roots plus bridge wiring should build an invoke draft");
assertDeepEqual(hiddenRootRefresh.draft, {
  endDayUtc: "2026-06-14",
  codexJsonlRoot: "synthetic/codex",
  claudeCodeJsonlRoot: "synthetic/claude-code",
  startedAt: "2026-06-14T00:00:00Z"
});
assertDeepEqual(hiddenRootRefresh.readiness.missingExplicitRoots, []);
assert(
  !JSON.stringify(hiddenRootRefresh.rows).includes("synthetic/codex"),
  "hidden root rows must not serialize Codex root values"
);
assert(
  !JSON.stringify(hiddenRootRefresh.rows).includes("synthetic/claude-code"),
  "hidden root rows must not serialize Claude Code root values"
);

const unwiredHiddenRootRefresh = buildManualRefreshDraftFromHiddenRoots({
  endDayUtc: "2026-06-14",
  codexJsonlRoot: "synthetic/codex",
  claudeCodeJsonlRoot: "synthetic/claude-code"
});
assert(!unwiredHiddenRootRefresh.canInvoke, "hidden roots should not invoke until bridge wiring is explicit");
assert(unwiredHiddenRootRefresh.draft === null, "unwired hidden root state should not expose an invoke draft");

const missingHiddenRootRefresh = buildManualRefreshDraftFromHiddenRoots(
  {
    endDayUtc: "2026-06-14",
    claudeCodeJsonlRoot: "synthetic/claude-code"
  },
  { hasTauriWiring: true }
);
assert(!missingHiddenRootRefresh.canInvoke, "missing Codex root should not expose an invoke draft");
assert(missingHiddenRootRefresh.draft === null, "missing root state should not expose a command draft");
assertDeepEqual(missingHiddenRootRefresh.readiness.missingExplicitRoots, ["codex"]);
assert(
  manualRefreshRootsLabel(missingHiddenRootRefresh.readiness) === "Missing Codex",
  "missing-root label should stay path-free"
);
assert(
  manualRefreshNeedsLabel(missingHiddenRootRefresh.readiness) === "Codex",
  "missing-root needs label should stay path-free"
);

const selectedSerialized = JSON.stringify(selectedRows);
assert(!selectedSerialized.includes("synthetic/codex"), "selected rows must not serialize Codex root values");
assert(
  !selectedSerialized.includes("synthetic/claude-code"),
  "selected rows must not serialize Claude Code root values"
);

const serialized = JSON.stringify({ explicitRootMockRows, manualRefreshMockState });
assert(!serialized.includes("C:/Users"), "mock setup state must not include local user paths");
assert(!serialized.includes("source_root"), "mock setup state must not include source roots");
assert(!serialized.includes("source_path"), "mock setup state must not include source paths");
assert(!serialized.includes("Documents"), "mock setup state must not include local directory names");
assert(!serialized.includes("AppData"), "mock setup state must not include local app data paths");
assert(!serialized.includes("secret"), "mock setup state must not include secret path markers");

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function assertDeepEqual(actual: unknown, expected: unknown) {
  const actualJson = JSON.stringify(actual);
  const expectedJson = JSON.stringify(expected);
  if (actualJson !== expectedJson) {
    throw new Error(`expected ${expectedJson}, got ${actualJson}`);
  }
}
