import type { ExplicitRootSelectionDraft } from "../data/source-setup.mock.js";

export const LOAD_SAVED_SOURCE_ROOTS_COMMAND = "load_saved_source_roots" as const;
export const SAVE_SOURCE_ROOTS_COMMAND = "save_source_roots" as const;
export const CLEAR_SAVED_SOURCE_ROOTS_COMMAND = "clear_saved_source_roots" as const;
export const DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES = 15;

export type SavedSourceRootsPayload = {
  codex_jsonl_root?: string;
  claude_code_jsonl_root?: string;
  auto_refresh_enabled: boolean;
  auto_refresh_interval_minutes: number;
};

export type SourceRootPreferences = {
  rootDraft: ExplicitRootSelectionDraft;
  hasSavedRoots: boolean;
  autoRefreshEnabled: boolean;
  autoRefreshIntervalMinutes: number;
};

export type SourceRootPersistenceState =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "loaded" }
  | { phase: "saving" }
  | { phase: "saved" }
  | { phase: "dirty" }
  | { phase: "failed"; message: string };

export function defaultSourceRootPreferences(): SourceRootPreferences {
  return {
    rootDraft: {},
    hasSavedRoots: false,
    autoRefreshEnabled: false,
    autoRefreshIntervalMinutes: DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES
  };
}

export function sourceRootPreferencesFromSaved(
  saved: Partial<SavedSourceRootsPayload>
): SourceRootPreferences {
  const rootDraft: ExplicitRootSelectionDraft = {};
  const codexRoot = normalizeRoot(saved.codex_jsonl_root);
  const claudeCodeRoot = normalizeRoot(saved.claude_code_jsonl_root);
  if (codexRoot) {
    rootDraft.codexJsonlRoot = codexRoot;
  }
  if (claudeCodeRoot) {
    rootDraft.claudeCodeJsonlRoot = claudeCodeRoot;
  }

  const hasBothRoots = Boolean(rootDraft.codexJsonlRoot && rootDraft.claudeCodeJsonlRoot);

  return {
    rootDraft,
    hasSavedRoots: Boolean(rootDraft.codexJsonlRoot || rootDraft.claudeCodeJsonlRoot),
    autoRefreshEnabled: Boolean(saved.auto_refresh_enabled) && hasBothRoots,
    autoRefreshIntervalMinutes: normalizeAutoRefreshIntervalMinutes(
      saved.auto_refresh_interval_minutes
    )
  };
}

export function savedSourceRootsPayloadFromPreferences(
  preferences: SourceRootPreferences
): SavedSourceRootsPayload {
  return {
    codex_jsonl_root: normalizeRoot(preferences.rootDraft.codexJsonlRoot),
    claude_code_jsonl_root: normalizeRoot(preferences.rootDraft.claudeCodeJsonlRoot),
    auto_refresh_enabled:
      preferences.autoRefreshEnabled &&
      Boolean(preferences.rootDraft.codexJsonlRoot && preferences.rootDraft.claudeCodeJsonlRoot),
    auto_refresh_interval_minutes: normalizeAutoRefreshIntervalMinutes(
      preferences.autoRefreshIntervalMinutes
    )
  };
}

export function sourceRootStorageLabel(
  preferences: SourceRootPreferences,
  state: SourceRootPersistenceState
) {
  if (state.phase === "loading") {
    return "Loading";
  }
  if (state.phase === "saving") {
    return "Saving";
  }
  if (state.phase === "dirty") {
    return "Unsaved changes";
  }
  if (state.phase === "failed") {
    return "Save unavailable";
  }
  return preferences.hasSavedRoots ? "Saved locally" : "This session";
}

export function autoRefreshStatusLabel(
  preferences: SourceRootPreferences,
  rootsAreSaved: boolean
) {
  if (!rootsAreSaved) {
    return "Needs saved roots";
  }
  return preferences.autoRefreshEnabled ? "On" : "Off";
}

export function shouldRunAutoRefresh({
  preferences,
  canInvoke,
  isRunning,
  rootsAreSaved
}: {
  preferences: SourceRootPreferences;
  canInvoke: boolean;
  isRunning: boolean;
  rootsAreSaved: boolean;
}) {
  return preferences.autoRefreshEnabled && rootsAreSaved && canInvoke && !isRunning;
}

export function canRunHeaderRefresh({
  canInvoke,
  isRunning,
  rootsAreSaved
}: {
  canInvoke: boolean;
  isRunning: boolean;
  rootsAreSaved: boolean;
}) {
  return canInvoke && rootsAreSaved && !isRunning;
}

export function headerRefreshButtonLabel(isRunning: boolean) {
  return isRunning ? "Refreshing" : "Refresh";
}

export function headerRefreshButtonTitle({
  canInvoke,
  isRunning,
  rootsAreSaved
}: {
  canInvoke: boolean;
  isRunning: boolean;
  rootsAreSaved: boolean;
}) {
  if (isRunning) {
    return "Refreshing local aggregate";
  }
  if (!canInvoke) {
    return "Save Codex and Claude roots in Sources first";
  }
  if (!rootsAreSaved) {
    return "Save roots before using header refresh";
  }
  return "Refresh local aggregate";
}

export function normalizeAutoRefreshIntervalMinutes(value: unknown) {
  const minutes = typeof value === "number" && Number.isFinite(value)
    ? Math.trunc(value)
    : DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES;
  if (minutes < 5) {
    return DEFAULT_AUTO_REFRESH_INTERVAL_MINUTES;
  }
  if (minutes > 1440) {
    return 1440;
  }
  return minutes;
}

function normalizeRoot(value: string | undefined) {
  const normalized = value?.trim();
  return normalized || undefined;
}
