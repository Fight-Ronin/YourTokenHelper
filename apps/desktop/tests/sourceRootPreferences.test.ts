import {
  CLEAR_SAVED_SOURCE_ROOTS_COMMAND,
  DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES,
  LOAD_SAVED_SOURCE_ROOTS_COMMAND,
  SAVE_SOURCE_ROOTS_COMMAND,
  autoRefreshStatusLabel,
  canRunHeaderRefresh,
  defaultSourceRootPreferences,
  headerRefreshButtonLabel,
  headerRefreshButtonTitle,
  normalizeAutoRefreshIntervalMinutes,
  savedSourceRootsPayloadFromPreferences,
  shouldRunAutoRefresh,
  sourceRootPreferencesFromSaved,
  sourceRootStorageLabel
} from "../src/commands/sourceRootPreferences.js";

assert(LOAD_SAVED_SOURCE_ROOTS_COMMAND === "load_saved_source_roots", "load command should be named");
assert(SAVE_SOURCE_ROOTS_COMMAND === "save_source_roots", "save command should be named");
assert(CLEAR_SAVED_SOURCE_ROOTS_COMMAND === "clear_saved_source_roots", "clear command should be named");
assert(DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES === 15, "auto refresh should default to a conservative interval");

const defaults = defaultSourceRootPreferences();
assertDeepEqual(defaults, {
  rootDraft: {},
  hasSavedRoots: false,
  autoRefreshEnabled: false,
  autoRefreshIntervalMinutes: 15
});
assert(sourceRootStorageLabel(defaults, { phase: "idle" }) === "This session", "missing roots stay session-only");
assert(autoRefreshStatusLabel(defaults, false) === "Needs saved roots", "auto refresh needs saved roots");

const preferences = sourceRootPreferencesFromSaved({
  codex_jsonl_root: " synthetic/codex ",
  claude_code_jsonl_root: " synthetic/claude-code ",
  gemini_cli_jsonl_root: " synthetic/gemini ",
  auto_refresh_enabled: true,
  auto_refresh_interval_minutes: 30
});

assertDeepEqual(preferences, {
  rootDraft: {
    codexJsonlRoot: "synthetic/codex",
    claudeCodeJsonlRoot: "synthetic/claude-code",
    geminiCliJsonlRoot: "synthetic/gemini"
  },
  hasSavedRoots: true,
  autoRefreshEnabled: true,
  autoRefreshIntervalMinutes: 30
});
assert(sourceRootStorageLabel(preferences, { phase: "loaded" }) === "Saved locally", "loaded roots should show saved");
assert(sourceRootStorageLabel(preferences, { phase: "dirty" }) === "Unsaved changes", "edited roots should show dirty");
assert(autoRefreshStatusLabel(preferences, true) === "On", "saved enabled roots should show auto on");
assert(
  shouldRunAutoRefresh({
    preferences,
    canInvoke: true,
    isRunning: false,
    rootsAreSaved: true
  }),
  "ready saved roots should allow auto refresh"
);
assert(
  !shouldRunAutoRefresh({
    preferences,
    canInvoke: true,
    isRunning: true,
    rootsAreSaved: true
  }),
  "running refresh should block auto refresh"
);
assert(
  canRunHeaderRefresh({
    canInvoke: true,
    isRunning: false,
    rootsAreSaved: true
  }),
  "header refresh should run when roots are saved and the command is ready"
);
assert(
  !canRunHeaderRefresh({
    canInvoke: true,
    isRunning: false,
    rootsAreSaved: false
  }),
  "header refresh should require saved roots"
);
assert(
  !canRunHeaderRefresh({
    canInvoke: true,
    isRunning: true,
    rootsAreSaved: true
  }),
  "header refresh should not start a second refresh while running"
);
assert(headerRefreshButtonLabel(false) === "Refresh", "header button should use refresh language");
assert(headerRefreshButtonLabel(true) === "Refreshing", "header button should show running state");
assert(
  headerRefreshButtonTitle({
    canInvoke: false,
    isRunning: false,
    rootsAreSaved: false
  }) === "Save at least one source root in Sources first",
  "header title should explain missing setup"
);
assert(
  headerRefreshButtonTitle({
    canInvoke: true,
    isRunning: false,
    rootsAreSaved: false
  }) === "Save roots before using header refresh",
  "header title should explain unsaved roots"
);
assert(
  headerRefreshButtonTitle({
    canInvoke: true,
    isRunning: true,
    rootsAreSaved: true
  }) === "Refreshing local aggregate",
  "header title should show running state"
);
assert(
  headerRefreshButtonTitle({
    canInvoke: true,
    isRunning: false,
    rootsAreSaved: true
  }) === "Refresh local aggregate",
  "header title should show ready state"
);

const savedPayload = savedSourceRootsPayloadFromPreferences(preferences);
assertDeepEqual(savedPayload, {
  codex_jsonl_root: "synthetic/codex",
  claude_code_jsonl_root: "synthetic/claude-code",
  gemini_cli_jsonl_root: "synthetic/gemini",
  auto_refresh_enabled: true,
  auto_refresh_interval_minutes: 30
});

const missingClaude = sourceRootPreferencesFromSaved({
  codex_jsonl_root: "synthetic/codex",
  auto_refresh_enabled: true,
  auto_refresh_interval_minutes: 2
});
assert(missingClaude.hasSavedRoots, "partial saved roots should be remembered");
assert(missingClaude.autoRefreshEnabled, "one saved root may enable auto refresh");
assert(
  missingClaude.autoRefreshIntervalMinutes === DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES,
  "too-short intervals should normalize to default"
);
assert(normalizeAutoRefreshIntervalMinutes(2000) === 1440, "interval should cap at one day");
assert(normalizeAutoRefreshIntervalMinutes("bad") === 15, "invalid interval should normalize to default");

const serializedPreferences = JSON.stringify({
  defaults,
  preferences: {
    ...preferences,
    rootDraft: {}
  },
  savedPayload: {
    auto_refresh_enabled: savedPayload.auto_refresh_enabled,
    auto_refresh_interval_minutes: savedPayload.auto_refresh_interval_minutes
  }
});
assert(!serializedPreferences.includes("C:/Users"), "preference labels must not include local user paths");
assert(!serializedPreferences.includes("Documents"), "preference labels must not include local directory names");
assert(!serializedPreferences.includes("AppData"), "preference labels must not include app data paths");

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
